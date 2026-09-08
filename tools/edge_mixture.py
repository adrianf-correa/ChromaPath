"""Candidato experimental; NÃO importado pelo pipeline de produção.

Testa a troca de misturas na borda externa pela cor de maior cobertura.
Uma mistura matemática não prova que um pixel seja antialias intencional.
"""

import cv2
import numpy as np


def snap_exterior_mixtures(rgba: np.ndarray) -> tuple[np.ndarray, int]:
    result = rgba.copy()
    border = np.concatenate((rgba[0], rgba[-1], rgba[:, 0], rgba[:, -1]))
    # A hipótese desta rodada só cobre fundo opaco e exatamente uniforme.
    if not np.all(border == border[0]) or border[0, 3] != 255:
        return result, 0
    background = border[0, :3]
    opaque = rgba[:, :, 3] == 255
    rgb = rgba[:, :, :3]
    exact_background = np.all(rgb == background, axis=2) & opaque
    _, labels = cv2.connectedComponents(exact_background.astype(np.uint8), connectivity=8)
    exterior = labels == labels[0, 0]
    kernel = np.ones((3, 3), np.uint8)
    flat = np.all(cv2.erode(rgb, kernel) == cv2.dilate(rgb, kernel), axis=2)
    flat &= cv2.erode(opaque.astype(np.uint8), kernel).astype(bool)
    stable_background = flat & exterior
    neighborhood = np.ones((5, 5), np.uint8)
    near_background = cv2.dilate(stable_background.astype(np.uint8), neighborhood).astype(bool)
    candidates = near_background & opaque & ~flat & ~exact_background
    colors, counts = np.unique(rgb[flat & ~exact_background], axis=0, return_counts=True)
    # Limites de custo/apoio da hipótese, não um número de cores de saída.
    colors = colors[counts >= 32]
    if len(colors) > 16:
        return result, 0
    best_error = np.full(opaque.shape, np.inf, dtype=np.float32)
    for color in colors:
        vector = color.astype(np.float32) - background
        length_squared = np.sum(vector**2)
        if length_squared < 32**2:
            continue
        stable_color = flat & np.all(rgb == color, axis=2)
        near_color = cv2.dilate(stable_color.astype(np.uint8), neighborhood).astype(bool)
        coverage = np.sum((rgb.astype(np.float32) - background) * vector, axis=2) / length_squared
        mixed = background + coverage[..., None] * vector
        error = np.max(np.abs(rgb - mixed), axis=2)
        eligible = (candidates & near_color & (coverage >= 0.05) & (coverage <= 0.95)
                    & (error <= 1.0) & (error < best_error))
        result[eligible, :3] = np.where(coverage[eligible, None] > 0.5, color, background)
        best_error[eligible] = error[eligible]
    return result, int(np.count_nonzero(np.any(result != rgba, axis=2)))
