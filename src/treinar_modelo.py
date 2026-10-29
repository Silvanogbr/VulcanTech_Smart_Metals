"""Treina e compara dois modelos simples para classificar o tipo de falha."""
from pathlib import Path
import json

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder

from pipeline import carregar_e_preparar

RAIZ = Path(__file__).resolve().parents[1]
COLUNAS = [
    "temperatura_fuso_c", "vibracao_triaxial_rms_mms", "torque_fuso_nm",
    "vazao_refrigerante_lmin", "corrente_estator_amp", "pressao_hidraulica_bar",
    "nivel_ruido_db", "iem", "vibracao_triaxial_rms_media_30min",
    "vibracao_triaxial_rms_desvio_2h", "torque_fuso_media_30min",
    "torque_fuso_desvio_2h", "vazao_refrigerante_media_30min",
    "vazao_refrigerante_desvio_2h",
]


def main():
    arquivo_preparado = RAIZ / "dados_processados" / "sensores_preparados.csv"
    if arquivo_preparado.exists():
        dados = pd.read_csv(arquivo_preparado, parse_dates=["timestamp"])
        print(f"Usando dados preparados: {arquivo_preparado}")
    else:
        dados, _ = carregar_e_preparar(RAIZ / "dados_sensores_vulcantech.csv")
    # Codificação simples para as duas colunas categóricas.
    dados["celula_codigo"] = LabelEncoder().fit_transform(dados["id_celula"])
    dados["liga_codigo"] = LabelEncoder().fit_transform(dados["liga_metalica"])
    colunas = COLUNAS + ["celula_codigo", "liga_codigo"]
    dados = dados.sort_values("timestamp")

    corte = int(len(dados) * 0.70)
    treino, teste = dados.iloc[:corte], dados.iloc[corte:]
    X_treino, y_treino = treino[colunas], treino["tipo_falha"]
    X_teste, y_teste = teste[colunas], teste["tipo_falha"]

    modelos = {
        "Random Forest": RandomForestClassifier(
            n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1
        ),
    }
    resultados = []
    relatorios = {}
    for nome, modelo in modelos.items():
        modelo.fit(X_treino, y_treino)
        predicao = modelo.predict(X_teste)
        relatorio = classification_report(y_teste, predicao, output_dict=True, zero_division=0)
        recall_falhas = sum(relatorio[str(classe)]["recall"] for classe in (1, 2, 3)) / 3
        resultados.append((recall_falhas, nome, modelo, predicao))
        relatorios[nome] = {
            "recall_medio_falhas": recall_falhas,
            "recall_por_classe": {str(classe): relatorio[str(classe)]["recall"] for classe in range(4)},
            "matriz_confusao": confusion_matrix(y_teste, predicao, labels=[0, 1, 2, 3]).tolist(),
        }
        print(f"\n{nome} - matriz de confusão (linhas=reais, colunas=previstas):")
        print(confusion_matrix(y_teste, predicao, labels=[0, 1, 2, 3]))
        print(classification_report(y_teste, predicao, zero_division=0))

    _, nome, melhor_modelo, predicao = max(resultados, key=lambda item: item[0])
    print(f"Modelo selecionado pelo recall médio das classes de falha: {nome}")
    print("Importância dos atributos:")
    print(pd.Series(melhor_modelo.feature_importances_, index=colunas).sort_values(ascending=False).head(10))

    # Métrica demonstrativa: penaliza disponibilidade pelas classes 1 e 3,
    # e qualidade pela classe 2. Não representa OEE real sem dados de produção.
    risco = pd.Series(predicao, index=teste.index)
    disponibilidade = 1 - risco.isin([1, 3]).mean()
    qualidade = 1 - (risco == 2).mean()
    oee_estimado = disponibilidade * qualidade
    print(f"OEE estimado demonstrativo: {oee_estimado:.3f} (disponibilidade x qualidade)")

    artefatos = RAIZ / "modelos"
    artefatos.mkdir(exist_ok=True)
    joblib.dump({"modelo": melhor_modelo, "colunas": colunas}, artefatos / "modelo_falhas.joblib")
    relatorio_final = {
        "modelo": nome,
        "recall_medio_falhas": relatorios[nome]["recall_medio_falhas"],
        "recall_por_classe": relatorios[nome]["recall_por_classe"],
        "matriz_confusao": relatorios[nome]["matriz_confusao"],
        "atributos_importantes": [
            {"nome": nome_atributo, "importancia": float(importancia)}
            for nome_atributo, importancia in pd.Series(melhor_modelo.feature_importances_, index=colunas)
            .sort_values(ascending=False).head(8).items()
        ],
        "modelos_comparados": {k: v["recall_medio_falhas"] for k, v in relatorios.items()},
    }
    (artefatos / "relatorio_modelo.json").write_text(json.dumps(relatorio_final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Modelo exportado em {artefatos / 'modelo_falhas.joblib'}")


if __name__ == "__main__":
    main()
