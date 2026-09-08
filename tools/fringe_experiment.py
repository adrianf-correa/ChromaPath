"""Isola a franja da fixture seam sem alterar o pipeline de produção."""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

import numpy as np
from PIL import Image
import vtracer

from src.preprocess import preprocess_colors
from src.svg_analysis import analyze_svg
from src.svg_postprocess import simplify_svg_colors
from src.vectorize import (SHARP_CORNER_THRESHOLD, VTRACER_COLOR_PRECISION,
                           VTRACER_HIERARCHICAL_MODE, preprocess_image)
from tools.geometry_experiment import read_labels, render
from tools.geometry_fixtures import reference_svg
from tools.geometry_metrics import geometry_metrics, path_complexity
from tools.edge_mixture import snap_exterior_mixtures


BACKEND_VARIANTS = {
    "layer0": {"layer_difference": 0},
    "layer4": {"layer_difference": 4},
    "layer8": {"layer_difference": 8},
    "precision8": {"color_precision": 8},
    "speckle0": {"filter_speckle": 0},
    "speckle1": {"filter_speckle": 1},
    "speckle2": {"filter_speckle": 2},
    "cutout": {"hierarchical": "cutout"},
}


def fringe_metrics(labels: np.ndarray, size: int, phase: float, scale: int) -> dict:
    """Faixas externas azuis longe da emenda; coral aqui é sempre indevido."""
    if scale <= 0 or labels.shape != (size * scale, size * scale) or not 0 <= phase < 1:
        raise ValueError("Dimensões, fase ou escala incompatíveis com a fixture")
    boxes = {"left": (18, 30, 24, 162), "top": (30, 18, 60, 24),
             "bottom": (30, 168, 60, 175)}
    result = {}
    for name, box in boxes.items():
        left, top, right, bottom = [round((v * size / 192 + phase) * scale) for v in box]
        roi = labels[top:bottom, left:right] == 2
        result[name] = dict(foreign_area_px=float(roi.sum() / scale**2),
                            affected_length_px=float(np.any(roi, axis=1 if name == "left" else 0).sum() / scale))
    return result


def trace(image: Image.Image, filter_speckle: int, **overrides) -> str:
    options = dict(mode="spline", filter_speckle=filter_speckle,
                   color_precision=VTRACER_COLOR_PRECISION,
                   hierarchical=VTRACER_HIERARCHICAL_MODE,
                   corner_threshold=SHARP_CORNER_THRESHOLD)
    options.update(overrides)
    return vtracer.convert_pixels_to_svg(list(image.get_flattened_data()), image.size, **options)


def run(output: Path, node: str, scale: int = 4) -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cases, jobs = [], []
    for size in (96, 192, 384):
        for phase in (0.0, 0.5):
            directory = output / f"seam-{size}-phase{phase:g}"
            directory.mkdir()
            source = directory / "reference.svg"
            source.write_text(reference_svg("seam", size, phase), encoding="utf-8")
            jobs.extend(dict(input=str(source), output=str(directory / name), scale=s)
                        for name, s in (("input.png", 1), ("reference.png", scale)))
            cases.append((size, phase, directory))
    versions = render(node, output, "references", jobs)
    jobs, rows = [], []
    for size, phase, directory in cases:
        report = preprocess_colors(directory / "input.png", directory / "prepared.png")
        original = preprocess_image(directory / "input.png")
        prepared = preprocess_image(directory / "prepared.png")
        raw = trace(prepared, report["filter_speckle"])
        snapped, snapped_pixels = snap_exterior_mixtures(np.asarray(prepared))
        Image.fromarray(snapped).save(directory / "snapped-input.png")
        variants = {"direct": trace(original, 4), "traced": raw,
                    "final": simplify_svg_colors(raw)[0],
                    "snap": simplify_svg_colors(trace(Image.fromarray(snapped), report["filter_speckle"]))[0]}
        for name, overrides in BACKEND_VARIANTS.items():
            options = {"filter_speckle": report["filter_speckle"], **overrides}
            variants[name] = simplify_svg_colors(trace(prepared, **options))[0]
        for name, svg in variants.items():
            source = directory / f"{name}.svg"
            source.write_text(svg, encoding="utf-8")
            jobs.append(dict(input=str(source), output=str(directory / f"{name}.png"), scale=scale))
        rows.append(dict(size=size, phase=phase, case=directory.name, preprocessing=report,
                         snapped_pixels=snapped_pixels,
                         raster_identical=bool(np.array_equal(np.asarray(original), np.asarray(prepared))),
                         direct_equals_traced=variants["direct"] == raw,
                         traced_equals_final=raw == variants["final"],
                         complexity={k: {**path_complexity(v), **analyze_svg(directory / f"{k}.svg")}
                                     for k, v in variants.items()}))
    render(node, output, "traces", jobs)
    for row in rows:
        directory = output / row["case"]
        reference = read_labels(directory / "reference.png")
        row["stages"] = {}
        for name in ("input", "prepared", *row["complexity"]):
            labels = read_labels(directory / f"{name}.png")
            if name in ("input", "prepared"):
                labels = np.repeat(np.repeat(labels, scale, axis=0), scale, axis=1)
            row["stages"][name] = dict(
                fringe=fringe_metrics(labels, row["size"], row["phase"], scale),
                **geometry_metrics(reference, labels, scale))
        print(row["case"], "raster unchanged:", row["raster_identical"],
              {name: round(sum(m["foreign_area_px"] for m in stage["fringe"].values()), 3)
               for name, stage in row["stages"].items()}, flush=True)
    source_names = ("fringe_experiment.py", "edge_mixture.py", "geometry_fixtures.py",
                    "geometry_metrics.py", "geometry_experiment.py", "render_geometry.cjs")
    result = dict(
        render_scale=scale, renderer_versions=versions,
        versions=dict(python=platform.python_version(), **{name: version(name) for name in
                      ("vtracer", "Pillow", "numpy", "opencv-python-headless")}),
        backend_variants=BACKEND_VARIANTS,
        source_sha256={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                       for name in source_names}, rows=rows)
    (output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--render-scale", type=int, choices=(4, 8), default=4)
    args = parser.parse_args()
    run(args.output, args.node, args.render_scale)


if __name__ == "__main__":
    main()
