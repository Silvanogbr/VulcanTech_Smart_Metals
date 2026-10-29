"""Funções básicas de inspeção de imagens de solda com OpenCV."""
import cv2
import numpy as np


def inspecionar_solda(imagem: np.ndarray) -> dict:
    """Mede bordas e áreas quentes de uma imagem; os limites devem ser calibrados."""
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    nitida = cv2.GaussianBlur(cinza, (3, 3), 0)
    bordas = cv2.Canny(nitida, 50, 150)
    contornos, _ = cv2.findContours(bordas, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    # Pequenos contornos fechados são tratados como possíveis poros, não como defeitos confirmados.
    areas = [cv2.contourArea(c) for c in contornos]
    possiveis_poros = [area for area in areas if 5 <= area <= 500]

    hsv = cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)
    # Máscara aproximada para amarelo/laranja/vermelho em imagens térmicas coloridas.
    faixa_quente = cv2.inRange(hsv, np.array([0, 80, 120]), np.array([40, 255, 255]))
    area_total = imagem.shape[0] * imagem.shape[1]
    percentual_quente = 100 * cv2.countNonZero(faixa_quente) / area_total

    return {
        "contornos_detectados": len(contornos),
        "poros_estimados": len(possiveis_poros),
        "area_dos_poros_percentual": round(100 * sum(possiveis_poros) / area_total, 3),
        "area_quente_percentual": round(percentual_quente, 2),
        "alerta_sobreaquecimento": percentual_quente > 10,
        "nota": "Resultado demonstrativo; calibrar limiares com imagens rotuladas da fábrica.",
    }
