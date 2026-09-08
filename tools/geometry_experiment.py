"""Ensaio isolado: python -m tools.geometry_experiment --output outputs/geometry/run1.

Não altera parâmetros do produto. Node + tools/package.json são opcionais e
necessários apenas para renderizar este ensaio. O relatório registra versões.
"""

import argparse
import csv
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
from PIL import Image
import vtracer

from src.preprocess import preprocess_colors
from src.svg_postprocess import simplify_svg_colors
from src.vectorize import (SHARP_CORNER_THRESHOLD, VTRACER_COLOR_PRECISION,
                           VTRACER_HIERARCHICAL_MODE, preprocess_image, vectorize_image)
from tools.geometry_fixtures import PALETTE, SCENES, SIZE, reference_svg
from tools.geometry_metrics import geometry_metrics, palette_labels, path_complexity

VARIANTS = {
    "current": {},
    "length6": {"length_threshold": 6.0},
    "length8": {"length_threshold": 8.0},
    "length10": {"length_threshold": 10.0},
    "corner60": {"corner_threshold": 60},
    "splice60": {"splice_threshold": 60},
}
RENDER_SCALE = 4


def experimental_trace(image: Image.Image, filter_speckle: int, overrides: dict) -> str:
    options = dict(mode="spline", filter_speckle=filter_speckle,
                   color_precision=VTRACER_COLOR_PRECISION,
                   hierarchical=VTRACER_HIERARCHICAL_MODE,
                   corner_threshold=SHARP_CORNER_THRESHOLD)
    options.update(overrides)
    svg = vtracer.convert_pixels_to_svg(list(image.get_flattened_data()), image.size, **options)
    return simplify_svg_colors(svg)[0]


def render(node: str, output: Path, name: str, jobs: list) -> dict:
    manifest = output / f"{name}-render-jobs.json"
    manifest.write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
    result = subprocess.run([node, str(Path(__file__).with_name("render_geometry.cjs")),
                             str(manifest)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def read_labels(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return palette_labels(np.asarray(image.convert("RGB")), PALETTE)


def run_experiment(output: Path, node: str, sizes: list[int], phases: list[float],
                   render_scale: int = RENDER_SCALE) -> dict:
    output = output.resolve()
    # Never silently replace a previous experiment or unrelated directory.
    output.mkdir(parents=True, exist_ok=False)
    cases, jobs = [], []
    for scene in SCENES:
        for size in sizes:
            for phase in phases:
                name = f"{scene}-{size}-phase{phase:g}"
                directory = output / name
                directory.mkdir()
                svg = directory / "reference.svg"
                svg.write_text(reference_svg(scene, size, phase), encoding="utf-8")
                jobs.extend(dict(input=str(svg), output=str(directory / target), scale=scale)
                            for target, scale in (("input.png", 1), ("reference.png", render_scale)))
                cases.append(dict(name=name, directory=directory, scene=scene, size=size, phase=phase))
    renderer_versions = render(node, output, "reference", jobs)
    jobs, trace_reports = [], {}
    for case in cases:
        directory = case["directory"]
        preprocessing = preprocess_colors(directory / "input.png", directory / "prepared.png")
        image = preprocess_image(directory / "prepared.png")
        # Use the real production entry point as control, not only its copied options.
        vectorize_image(directory / "prepared.png", directory / "current.svg",
                        filter_speckle=preprocessing["filter_speckle"])
        control = (directory / "current.svg").read_text(encoding="utf-8")
        if experimental_trace(image, preprocessing["filter_speckle"], {}) != control:
            raise AssertionError("O controle experimental divergiu da produção")
        trace_reports[case["name"]] = {}
        for variant, overrides in VARIANTS.items():
            svg = control if variant == "current" else experimental_trace(
                image, preprocessing["filter_speckle"], overrides)
            path = directory / f"{variant}.svg"
            path.write_text(svg, encoding="utf-8")
            trace_reports[case["name"]][variant] = dict(
                **path_complexity(svg), bytes=path.stat().st_size)
            jobs.append(dict(input=str(path), output=str(directory / f"{variant}.png"), scale=render_scale))
        case["preprocessing"] = preprocessing
        print(f'Traced {case["name"]}', flush=True)
    render(node, output, "traces", jobs)
    rows = []
    for case in cases:
        directory = case["directory"]
        reference = read_labels(directory / "reference.png")
        for variant in VARIANTS:
            actual = read_labels(directory / f"{variant}.png")
            if actual.shape != reference.shape:
                raise AssertionError("Render de saída não coincide com dimensões da referência")
            local = {}
            for name, box in SCENES[case["scene"]]["regions"].items():
                coords = [round((v * case["size"] / SIZE + case["phase"]) * render_scale) for v in box]
                left, top, right, bottom = coords
                ref_roi, actual_roi = reference[top:bottom, left:right], actual[top:bottom, left:right]
                local[name] = dict(
                    mismatch_area_px=float(np.count_nonzero(ref_roi != actual_roi) / render_scale**2),
                    uncovered_area_px=float(np.count_nonzero((ref_roi != 0) & (actual_roi == 0)) / render_scale**2))
            rows.append(dict(case=case["name"], scene=case["scene"], size=case["size"], phase=case["phase"],
                             variant=variant, **trace_reports[case["name"]][variant],
                             **geometry_metrics(reference, actual, render_scale), local=local))
        print(f'Measured {case["name"]}', flush=True)
    sources = [Path(__file__), Path(__file__).with_name("geometry_fixtures.py"),
               Path(__file__).with_name("geometry_metrics.py"), Path(__file__).with_name("render_geometry.cjs")]
    report = dict(
        versions=dict(python=platform.python_version(), **{name: version(name) for name in
                      ("vtracer", "Pillow", "numpy", "opencv-python-headless")}, renderer=renderer_versions),
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        settings=dict(render_scale=render_scale, sizes=sizes, phases=phases, variants=VARIANTS,
                      corner_threshold=SHARP_CORNER_THRESHOLD, color_precision=VTRACER_COLOR_PRECISION,
                      hierarchical=VTRACER_HIERARCHICAL_MODE),
        preprocessing={c["name"]: c["preprocessing"] for c in cases}, rows=rows)
    (output / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=("case", "variant", "segments", "bytes",
                                                 "mismatch_area_px", "silhouette_max_px",
                                                 "color_boundary_max_px"))
        writer.writeheader()
        for row in rows:
            maxima = [region["boundary_max_px"] for region in row["regions"].values()]
            writer.writerow(dict(
                **{key: row[key] for key in ("case", "variant", "segments", "bytes", "mismatch_area_px")},
                silhouette_max_px=row["silhouette"]["boundary_max_px"],
                color_boundary_max_px=None if None in maxima else max(maxima, default=0)))
    print("Variant     Segments  Mean mismatched image area (%)")
    for variant in VARIANTS:
        selected = [row for row in rows if row["variant"] == variant]
        mean = sum(row["mismatch_area_px"] / row["size"]**2 for row in selected) / len(selected)
        print(f'{variant:<12}{sum(row["segments"] for row in selected):>8}  {100 * mean:.4f}')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Diretório novo para este ensaio")
    parser.add_argument("--node", default="node", help="Executável Node.js (somente desenvolvimento)")
    parser.add_argument("--sizes", type=int, nargs="+", default=[96, 192, 384])
    parser.add_argument("--phases", type=float, nargs="+", default=[0.0, 0.5])
    parser.add_argument("--render-scale", type=int, default=RENDER_SCALE,
                        help="Escala de medição; 4 padrão, 8 para conferir amostragem")
    args = parser.parse_args()
    if any(size < 32 or size > 1024 for size in args.sizes):
        parser.error("Use resoluções entre 32 e 1024")
    if any(not 0 <= phase < 1 for phase in args.phases):
        parser.error("Use fases entre 0 (inclusive) e 1 (exclusive)")
    if not 1 <= args.render_scale <= 8:
        parser.error("Use escala de renderização entre 1 e 8")
    run_experiment(args.output, args.node, args.sizes, args.phases, args.render_scale)
    print(f'Relatório: {args.output / "report.json"}')


if __name__ == "__main__":
    main()
