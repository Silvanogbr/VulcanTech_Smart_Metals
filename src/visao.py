"""Triagem visual experimental de cordões de solda usando OpenCV."""
import base64

import cv2
import numpy as np


def analisar_imagem_solda(imagem: np.ndarray, roi: tuple[int, int, int, int] | None = None) -> dict:
    """Gera um mapa visual de contraste e uma triagem heurística da região selecionada.

    O mapa mostra variações locais da imagem; não representa temperatura real.
    """
    altura, largura = imagem.shape[:2]
    if roi:
        x, y, w, h = roi
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(largura, x + w), min(altura, y + h)
        if x2 <= x1 or y2 <= y1:
            raise ValueError("A área selecionada está fora da imagem.")
        recorte = imagem[y1:y2, x1:x2].copy()
    else:
        recorte = imagem.copy()

    h, w = recorte.shape[:2]
    if max(h, w) > 1100:
        escala = 1100 / max(h, w)
        recorte = cv2.resize(recorte, (int(w * escala), int(h * escala)))

    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    suavizada = cv2.GaussianBlur(cinza, (5, 5), 0)
    bordas = cv2.Canny(suavizada, 50, 140)
    contornos, _ = cv2.findContours(bordas, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # Estimativa simples de cavidades pequenas e arredondadas. Bordas próximas
    # do mesmo ponto são agrupadas para reduzir a contagem duplicada.
    poros = []
    for contorno in contornos:
        area = cv2.contourArea(contorno)
        perimetro = cv2.arcLength(contorno, True)
        if not 20 <= area <= 400 or perimetro == 0:
            continue
        circularidade = 4 * np.pi * area / (perimetro * perimetro)
        momentos = cv2.moments(contorno)
        if circularidade < 0.55 or momentos["m00"] == 0:
            continue
        centro = (momentos["m10"] / momentos["m00"], momentos["m01"] / momentos["m00"])
        if not any(np.hypot(centro[0] - px, centro[1] - py) < 10 for px, py, _ in poros):
            poros.append((*centro, area))

    total = h * w
    area_porosa = 100 * sum(item[2] for item in poros) / total
    densidade_bordas = 100 * cv2.countNonZero(bordas) / total
    nitidez = float(cv2.Laplacian(cinza, cv2.CV_64F).var())

    # Mapa falso-cor feito a partir de diferenças locais, suavizado para reduzir
    # o ruído da superfície. Só os pontos de maior contraste recebem a cor.
    fundo_local = cv2.GaussianBlur(cinza, (0, 0), 9)
    detalhe = cv2.absdiff(cinza, fundo_local)
    detalhe = cv2.medianBlur(detalhe, 7)
    detalhe = cv2.GaussianBlur(detalhe, (0, 0), 4)
    corte = float(np.percentile(detalhe, 88))
    limite = max(float(np.percentile(detalhe, 99.5)), corte + 1)
    intensidade = np.clip((detalhe.astype(np.float32) - corte) * 255 / (limite - corte), 0, 255).astype(np.uint8)
    mapa = cv2.applyColorMap(intensidade, cv2.COLORMAP_INFERNO)
    mascara = intensidade > 24
    sobreposicao = recorte.copy()
    misturada = cv2.addWeighted(recorte, 0.58, mapa, 0.42, 0)
    sobreposicao[mascara] = misturada[mascara]

    motivos = []
    if min(h, w) < 80 or nitidez < 5:
        avaliacao = "Imagem inconclusiva"
        motivos.append("A região está pequena ou sem nitidez suficiente para a triagem.")
    else:
        if len(poros) >= 5:
            motivos.append("Foram encontrados vários contornos pequenos e arredondados que podem indicar poros.")
        if area_porosa >= 0.5:
            motivos.append("A área estimada desses contornos passou do limite inicial do filtro.")
        if motivos:
            avaliacao = "Revisar a solda"
        else:
            avaliacao = "Sem alerta visual pelo filtro"
            motivos.append("O filtro não encontrou um número elevado de pequenos contornos arredondados.")

    sucesso, buffer = cv2.imencode(".png", sobreposicao)
    if not sucesso:
        raise ValueError("Não foi possível gerar a imagem de resultado.")

    return {
        "avaliacao": avaliacao,
        "motivos": motivos,
        "possiveis_poros": len(poros),
        "area_porosa_estimada_percentual": round(area_porosa, 3),
        "densidade_bordas_percentual": round(densidade_bordas, 2),
        "nitidez": round(nitidez, 1),
        "mapa_visual_base64": base64.b64encode(buffer).decode("ascii"),
        "observacao": "Triagem heurística de imagem RGB; as cores mostram contraste visual, não temperatura. Não substitui inspeção ou critério técnico de aceitação.",
    }
