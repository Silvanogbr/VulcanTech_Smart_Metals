"""Limpeza e criação de atributos para os sensores da VulcanTech."""
from pathlib import Path

import pandas as pd

SENSORES = [
    "temperatura_fuso_c",
    "vibracao_triaxial_rms_mms",
    "torque_fuso_nm",
    "vazao_refrigerante_lmin",
    "corrente_estator_amp",
    "pressao_hidraulica_bar",
    "nivel_ruido_db",
]

# Limites físicos indicados no enunciado. Valores fora da faixa são tratados como ausentes.
LIMITES = {
    "temperatura_fuso_c": (30, 75),
    "vibracao_triaxial_rms_mms": (0.8, 3.8),
    "torque_fuso_nm": (45, 210),
    "vazao_refrigerante_lmin": (15, 40),
    "corrente_estator_amp": (12, 55),
    "pressao_hidraulica_bar": (110, 220),
    "nivel_ruido_db": (45, 85),
}


def carregar_e_preparar(caminho_csv: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    dados = pd.read_csv(caminho_csv, parse_dates=["timestamp"])
    ausencias = (
        dados.groupby(["id_celula", "liga_metalica"])[SENSORES]
        .apply(lambda grupo: grupo.isna().mean().mul(100).round(2))
        .reset_index()
    )

    dados = dados.sort_values(["id_celula", "timestamp"]).copy()
    for coluna, (minimo, maximo) in LIMITES.items():
        fora_faixa = ~dados[coluna].between(minimo, maximo)
        dados.loc[fora_faixa, coluna] = pd.NA

    # Z-score calculado dentro de cada liga para não confundir material duro com falha.
    for coluna in SENSORES:
        media = dados.groupby("liga_metalica")[coluna].transform("mean")
        desvio = dados.groupby("liga_metalica")[coluna].transform("std").replace(0, 1)
        z_score = (dados[coluna] - media) / desvio
        dados.loc[z_score.abs() > 3, coluna] = pd.NA

    # Interpolação temporal dentro de cada célula; limite de até 2 amostras (10 min).
    dados = dados.set_index("timestamp")
    for coluna in SENSORES:
        dados[coluna] = dados.groupby("id_celula", group_keys=False)[coluna].apply(
            lambda serie: serie.interpolate(method="time", limit=2, limit_area="inside")
        )
    dados = dados.reset_index().sort_values("timestamp").reset_index(drop=True)
    # Para lacunas maiores que 10 min ou nas bordas, usa a mediana da própria célula.
    for coluna in SENSORES:
        mediana_celula = dados.groupby("id_celula")[coluna].transform("median")
        dados[coluna] = dados[coluna].fillna(mediana_celula).fillna(dados[coluna].median())

    for coluna in ["vibracao_triaxial_rms_mms", "torque_fuso_nm", "vazao_refrigerante_lmin"]:
        nome = coluna.removesuffix("_mms").removesuffix("_nm").removesuffix("_lmin")
        dados[f"{nome}_media_30min"] = dados.groupby("id_celula")[coluna].transform(
            lambda s: s.rolling(6, min_periods=1).mean()
        )
        dados[f"{nome}_desvio_2h"] = dados.groupby("id_celula")[coluna].transform(
            lambda s: s.rolling(24, min_periods=2).std()
        ).fillna(0)

    dados["iem"] = (
        dados["torque_fuso_nm"] * dados["vibracao_triaxial_rms_mms"]
        / (dados["vazao_refrigerante_lmin"] + 1)
    )
    # Razão pela média histórica da própria liga (a média é calculada sobre o conjunto disponível).
    for coluna in SENSORES:
        media_liga = dados.groupby("liga_metalica")[coluna].transform("mean").replace(0, 1)
        dados[f"{coluna}_normalizado_liga"] = dados[coluna] / media_liga
    return dados, ausencias


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    dados, ausencias = carregar_e_preparar(raiz / "dados_sensores_vulcantech.csv")
    pasta = raiz / "dados_processados"
    pasta.mkdir(exist_ok=True)
    dados.to_csv(pasta / "sensores_preparados.csv", index=False)
    ausencias.to_csv(pasta / "ausencias_por_celula_liga.csv", index=False)
    print(f"Registros processados: {len(dados)}")
    print(f"Arquivos salvos em: {pasta}")
