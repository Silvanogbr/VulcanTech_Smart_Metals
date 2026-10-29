"""API REST simples para inferência e inspeção de imagens."""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from visao import inspecionar_solda

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_MODELO = RAIZ / "modelos" / "modelo_falhas.joblib"
app = FastAPI(title="VulcanTech - demonstração de manutenção preditiva")
NOMES_FALHA = {0: "Normal", 1: "Desgaste de ferramenta", 2: "Falha de refrigeração", 3: "Desalinhamento ou trinca"}


class LeituraSensor(BaseModel):
    id_celula: str
    liga_metalica: str
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
def predict(leitura: LeituraSensor):
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
    linha["celula_codigo"] = int(v["id_celula"].replace("CEL-", "")) - 201
    ligas = {"Aco_Carbono_316L": 0, "Aluminio_7075": 1, "Liga_Titanio_Ti6Al4V": 2}
    linha["liga_codigo"] = ligas.get(v["liga_metalica"], 0)
    linha = {c: linha.get(c, 0) for c in colunas}
    entrada = pd.DataFrame([linha])
    classe = int(modelo.predict(entrada)[0])
    confianca = float(np.max(modelo.predict_proba(entrada)[0]))
    return {"tipo_falha": classe, "descricao": NOMES_FALHA.get(classe, "Desconhecida"), "confianca": round(confianca, 3)}


@app.post("/inspect/weld")
async def inspect_weld(imagem: UploadFile = File(...)):
    conteudo = await imagem.read()
    matriz = np.frombuffer(conteudo, dtype=np.uint8)
    imagem_cv = cv2.imdecode(matriz, cv2.IMREAD_COLOR)
    if imagem_cv is None:
        raise HTTPException(status_code=400, detail="Envie uma imagem válida (PNG ou JPEG).")
    return inspecionar_solda(imagem_cv)
