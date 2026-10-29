"""API REST simples para inferência e inspeção de imagens."""
from pathlib import Path
import json
from typing import Literal
import secrets

import cv2
import joblib
import numpy as np
import pandas as pd
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pipeline import SENSORES, carregar_e_preparar
from visao import analisar_imagem_solda

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_MODELO = RAIZ / "modelos" / "modelo_falhas.joblib"
ARQUIVO_RELATORIO = RAIZ / "modelos" / "relatorio_modelo.json"
app = FastAPI(title="VulcanTech - demonstração de manutenção preditiva")
SESSOES_DEMO: set[str] = set()
NOMES_FALHA = {0: "Normal", 1: "Desgaste de ferramenta", 2: "Falha de refrigeração", 3: "Desalinhamento ou trinca"}
WEB = RAIZ / "web"
app.mount("/static", StaticFiles(directory=WEB), name="static")
app.mount("/assets", StaticFiles(directory=RAIZ / "assets"), name="assets")
@app.middleware("http")
async def proteger_site_com_login_demo(request, call_next):
    caminho = request.url.path
    token = request.cookies.get("vulcantech_demo")
    autenticado = token in SESSOES_DEMO

    if request.method == "OPTIONS" or caminho in ("/demo-login", "/health"):
        return await call_next(request)
    if caminho.startswith(("/static/", "/assets/")):
        return await call_next(request)
    if caminho == "/login":
        if autenticado:
            return RedirectResponse("/dashboard", status_code=303)
        return await call_next(request)
    if not autenticado:
        if caminho.startswith("/api/"):
            return JSONResponse({"detail": "Faça o acesso demonstrativo para continuar."}, status_code=401)
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:8501", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/demo-login")
def demo_login(email: str = Form(...), senha: str = Form(...)):
    # O acesso é cenográfico: exige o envio do formulário, mas não valida conta real.
    if not email.strip() or not senha.strip():
        raise HTTPException(status_code=400, detail="Preencha e-mail e senha para continuar.")
    token = secrets.token_urlsafe(32)
    SESSOES_DEMO.add(token)
    resposta = JSONResponse({"ok": True})
    resposta.set_cookie(
        "vulcantech_demo", token, httponly=True, samesite="lax",
        max_age=8 * 60 * 60, path="/"
    )
    return resposta


@app.get("/")
def dashboard():
    return FileResponse(WEB / "index.html")


@app.get("/login")
def login_page():
    return FileResponse(WEB / "login.html")


@app.get("/dashboard")
def dashboard_page():
    return FileResponse(WEB / "dashboard.html")


@app.get("/sensors")
def sensors_page():
    return FileResponse(WEB / "sensors.html")


@app.get("/inspection")
def inspection_page():
    return FileResponse(WEB / "inspection.html")


@app.get("/api/dashboard-data")
def dashboard_data():
    arquivo_preparado = RAIZ / "dados_processados" / "sensores_preparados.csv"
    if arquivo_preparado.exists():
        dados = pd.read_csv(arquivo_preparado, parse_dates=["timestamp"])
    else:
        dados, _ = carregar_e_preparar(RAIZ / "dados_sensores_vulcantech.csv")
    original = pd.read_csv(RAIZ / "dados_sensores_vulcantech.csv")
    missing_rate = 100 * original[SENSORES].isna().sum().sum() / (len(original) * len(SENSORES))
    colunas = ["timestamp", "id_celula", "liga_metalica", *SENSORES, "iem", "tipo_falha"]
    dados = dados[colunas].copy()
    dados["timestamp"] = dados["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return {"rows": dados.to_dict(orient="records"), "missing_rate": round(missing_rate, 3)}


@app.get("/api/model-report")
def model_report():
    if not ARQUIVO_RELATORIO.exists():
        return {"disponivel": False, "mensagem": "Rode python src/treinar_modelo.py para gerar as métricas."}
    return {"disponivel": True, **json.loads(ARQUIVO_RELATORIO.read_text(encoding="utf-8"))}


class LeituraSensor(BaseModel):
    id_celula: Literal["CEL-201", "CEL-202", "CEL-203", "CEL-204"] = Field(
        description="Célula de manufatura existente no conjunto de dados"
    )
    liga_metalica: Literal[
        "Aco_Carbono_316L", "Aluminio_7075", "Liga_Titanio_Ti6Al4V"
    ] = Field(description="Liga metálica processada")
    temperatura_fuso_c: float
    vibracao_triaxial_rms_mms: float
    torque_fuso_nm: float
    vazao_refrigerante_lmin: float
    corrente_estator_amp: float
    pressao_hidraulica_bar: float
    nivel_ruido_db: float


@app.get("/health")
def health():
    return {"status": "ok", "modelo_disponivel": ARQUIVO_MODELO.exists()}


@app.post("/predict")
def predict(leitura: LeituraSensor = Body(
    openapi_examples={
        "leitura_valida": {
            "summary": "Leitura válida de exemplo",
            "value": {
                "id_celula": "CEL-201",
                "liga_metalica": "Aco_Carbono_316L",
                "temperatura_fuso_c": 56.0,
                "vibracao_triaxial_rms_mms": 1.9,
                "torque_fuso_nm": 100.0,
                "vazao_refrigerante_lmin": 29.0,
                "corrente_estator_amp": 28.0,
                "pressao_hidraulica_bar": 160.0,
                "nivel_ruido_db": 53.0,
            },
        }
    }
)):
    if not ARQUIVO_MODELO.exists():
        raise HTTPException(status_code=503, detail="Execute primeiro: python src/treinar_modelo.py")
    pacote = joblib.load(ARQUIVO_MODELO)
    modelo, colunas = pacote["modelo"], pacote["colunas"]
    v = leitura.model_dump()
    linha = {
        "temperatura_fuso_c": v["temperatura_fuso_c"],
        "vibracao_triaxial_rms_mms": v["vibracao_triaxial_rms_mms"],
        "torque_fuso_nm": v["torque_fuso_nm"],
        "vazao_refrigerante_lmin": v["vazao_refrigerante_lmin"],
        "corrente_estator_amp": v["corrente_estator_amp"],
        "pressao_hidraulica_bar": v["pressao_hidraulica_bar"],
        "nivel_ruido_db": v["nivel_ruido_db"],
    }
    linha["iem"] = linha["torque_fuso_nm"] * linha["vibracao_triaxial_rms_mms"] / (linha["vazao_refrigerante_lmin"] + 1)
    for base, valor in (("vibracao_triaxial_rms", linha["vibracao_triaxial_rms_mms"]),
                        ("torque_fuso", linha["torque_fuso_nm"]),
                        ("vazao_refrigerante", linha["vazao_refrigerante_lmin"])):
        linha[f"{base}_media_30min"] = valor
        linha[f"{base}_desvio_2h"] = 0
    celulas = {"CEL-201": 0, "CEL-202": 1, "CEL-203": 2, "CEL-204": 3}
    linha["celula_codigo"] = celulas[v["id_celula"]]
    ligas = {"Aco_Carbono_316L": 0, "Aluminio_7075": 1, "Liga_Titanio_Ti6Al4V": 2}
    linha["liga_codigo"] = ligas[v["liga_metalica"]]
    linha = {c: linha.get(c, 0) for c in colunas}
    entrada = pd.DataFrame([linha])
    classe = int(modelo.predict(entrada)[0])
    confianca = float(np.max(modelo.predict_proba(entrada)[0]))
    return {"tipo_falha": classe, "descricao": NOMES_FALHA.get(classe, "Desconhecida"), "confianca": round(confianca, 3)}


@app.post("/inspect/weld")
async def inspect_weld(
    imagem: UploadFile = File(...),
    roi_x: int | None = Form(None),
    roi_y: int | None = Form(None),
    roi_w: int | None = Form(None),
    roi_h: int | None = Form(None),
):
    conteudo = await imagem.read()
    matriz = np.frombuffer(conteudo, dtype=np.uint8)
    imagem_cv = cv2.imdecode(matriz, cv2.IMREAD_COLOR)
    if imagem_cv is None:
        raise HTTPException(status_code=400, detail="Envie uma imagem válida (PNG ou JPEG).")
    coordenadas = (roi_x, roi_y, roi_w, roi_h)
    if any(v is not None for v in coordenadas) and not all(v is not None for v in coordenadas):
        raise HTTPException(status_code=422, detail="Envie os quatro valores da região selecionada.")
    roi = tuple(coordenadas) if all(v is not None for v in coordenadas) else None
    try:
        return analisar_imagem_solda(imagem_cv, roi)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
