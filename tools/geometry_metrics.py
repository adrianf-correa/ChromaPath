"""Diagnóstico experimental, não usado pelo pipeline de produção."""

from collections import Counter
import re
import xml.etree.ElementTree as ET

import cv2
import numpy as np


def path_complexity(svg: str) -> dict:
    """Conta segmentos explícitos/implícitos M/L/C/Z do VTracer 0.6.15.

    Não chama isso de 'nós': C tem dois controles e uma âncora; Z pode ter
    comprimento zero. Outros comandos falham explicitamente, não são ignorados.
    """
    counts = Counter(subpaths=0, line_segments=0, cubic_segments=0, closes=0)
    token_pattern = re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
    for element in ET.fromstring(svg).iter():
        if element.tag.rsplit("}", 1)[-1] != "path":
            continue
        data = element.get("d", "")
        if token_pattern.sub("", data).strip(" ,\t\r\n"):
            raise ValueError("Dados de path inválidos")
        tokens = token_pattern.findall(data)
        index = 0
        while index < len(tokens):
            command = tokens[index].upper()
            if command not in ("M", "L", "C", "Z"):
                raise ValueError(f"Comando não suportado no diagnóstico: {command}")
            index += 1
            start = index
            while index < len(tokens) and not tokens[index].isalpha():
                index += 1
            size = index - start
            if command == "Z":
                if size:
                    raise ValueError("Z não recebe coordenadas")
                counts["closes"] += 1
                continue
            arity = 6 if command == "C" else 2
            if not size or size % arity:
                raise ValueError(f"Coordenadas incompletas de {command}")
            groups = size // arity
            if command == "M":
                counts["subpaths"] += 1
                counts["line_segments"] += groups - 1
            else:
                counts["cubic_segments" if command == "C" else "line_segments"] += groups
    counts["segments"] = counts["line_segments"] + counts["cubic_segments"]
    return dict(counts)


def palette_labels(rgb: np.ndarray, palette: tuple) -> np.ndarray:
    """Estima cobertura de cor nas fixtures, considerando misturas de antialias.

    Cor mais próxima isolada pode confundir uma mistura azul/branco com coral.
    Projeta nos segmentos RGB de cada par e escolhe a cor com >50% de cobertura
    no par de menor resíduo. Não é um quantizador geral para imagens reais.
    """
    colors = np.asarray(palette, dtype=np.float32)
    if len(colors) < 2 or len(np.unique(colors, axis=0)) != len(colors):
        raise ValueError("A paleta deve conter pelo menos duas cores distintas")
    pixels = rgb.astype(np.float32)
    best = np.full(pixels.shape[:2], np.inf, dtype=np.float32)
    labels = np.zeros(pixels.shape[:2], dtype=np.uint8)
    for left in range(len(colors)):
        for right in range(left + 1, len(colors)):
            vector = colors[right] - colors[left]
            coverage = np.clip(np.sum((pixels - colors[left]) * vector, axis=-1)
                               / np.sum(vector**2), 0, 1)
            mixed = colors[left] + coverage[..., None] * vector
            residual = np.sum((pixels - mixed)**2, axis=-1)
            better = residual < best
            labels[better] = np.where(coverage > 0.5, right, left)[better]
            best[better] = residual[better]
    return labels


def mask_metrics(reference: np.ndarray, actual: np.ndarray, scale: int = 1) -> dict:
    """Desvio simétrico de borda em pixels da entrada, não do render ampliado.

    Média/p95 podem ocultar pontas: também retornar máximo e regiões ausentes.
    A borda é amostrada numa grade, portanto não é Hausdorff vetorial exato.
    """
    if reference.shape != actual.shape or reference.ndim != 2 or scale <= 0:
        raise ValueError("Máscaras devem ter o mesmo tamanho 2D e escala positiva")
    reference, actual = reference.astype(bool), actual.astype(bool)
    result = {
        "xor_area_px": float(np.count_nonzero(reference != actual) / scale**2),
        "missing_region": bool(reference.any() and not actual.any()),
        "unexpected_region": bool(actual.any() and not reference.any()),
    }
    if not reference.any() or not actual.any():
        value = 0.0 if not reference.any() and not actual.any() else None
        return dict(result, boundary_mean_px=value, boundary_p95_px=value, boundary_max_px=value)
    kernel = np.ones((3, 3), np.uint8)
    def boundary(mask):
        return mask & ~cv2.erode(mask.astype(np.uint8), kernel,
                                borderType=cv2.BORDER_CONSTANT, borderValue=0).astype(bool)
    ref_edge, actual_edge = boundary(reference), boundary(actual)
    to_ref = cv2.distanceTransform((~ref_edge).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    to_actual = cv2.distanceTransform((~actual_edge).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    distances = np.concatenate((to_ref[actual_edge], to_actual[ref_edge])) / scale
    return dict(result, boundary_mean_px=float(distances.mean()),
                boundary_p95_px=float(np.percentile(distances, 95)),
                boundary_max_px=float(distances.max()))


def geometry_metrics(reference: np.ndarray, actual: np.ndarray, scale: int) -> dict:
    """Rótulo 0 = fundo; mede separadamente cada região de cor, incluindo ausentes."""
    labels = sorted(set(np.unique(reference)) | set(np.unique(actual)))
    return {
        "silhouette": mask_metrics(reference != 0, actual != 0, scale),
        "regions": {str(label): mask_metrics(reference == label, actual == label, scale)
                    for label in labels if label != 0},
        "uncovered_area_px": float(np.count_nonzero((reference != 0) & (actual == 0)) / scale**2),
        "mismatch_area_px": float(np.count_nonzero(reference != actual) / scale**2),
    }
