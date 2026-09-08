"""Formas originais redistribuíveis; coordenadas em um plano de 192 × 192.

O SVG é a referência, nunca a saída de outro vetorizador. As versões raster
são geradas pelo ensaio; não dependem das imagens locais privadas de samples/.
"""

PALETTE = ((255, 255, 255), (20, 61, 105), (239, 101, 72))
SIZE = 192
SCENES = {
    "arcs": {
        "body": '<circle cx="96" cy="96" r="73" fill="#143d69"/>'
                '<circle cx="96" cy="96" r="53" fill="white"/>'
                '<circle cx="96" cy="96" r="17" fill="#ef6548"/>',
        "regions": {"small_circle": (74, 74, 118, 118)},
    },
    "tips": {
        "body": '<path fill="#143d69" d="M96 10 L107 70 L169 57 '
                'L123 98 L170 153 L109 126 L96 183 L81 125 '
                'L20 150 L68 97 L22 55 L83 70 Z"/>',
        "regions": {"top_tip": (84, 5, 110, 43),
                    "bottom_tip": (82, 151, 110, 188)},
    },
    "diagonals": {
        "body": '<path fill="#143d69" d="M17 35 L169 78 L165 94 L13 51 Z"/>'
                '<path fill="#ef6548" d="M28 158 L150 108 L157 124 L35 174 Z"/>',
        "regions": {"acute_corner": (145, 66, 179, 102)},
    },
    "seam": {
        "body": '<path fill="#143d69" d="M20 20 H172 V172 H20 Z"/>'
                '<path fill="#ef6548" d="M96 20 C155 60 37 132 96 172 H172 V20 Z"/>',
        "regions": {"seam": (64, 30, 128, 162)},
    },
}


def reference_svg(scene: str, size: int, phase: float = 0.0) -> str:
    """phase desloca a arte em pixels da entrada, sem mudar sua forma."""
    offset = phase * SIZE / size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
        f'height="{size}" viewBox="0 0 {SIZE} {SIZE}">'
        '<rect width="192" height="192" fill="white"/>'
        f'<g transform="translate({offset} {offset})">'
        f'{SCENES[scene]["body"]}</g></svg>'
    )
