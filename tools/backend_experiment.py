"""Compare isolated Rust merge experiments with the installed VTracer control.

No production module or dependency is replaced. Build tools/backend_probe first.
"""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np
from PIL import Image

from src.preprocess import preprocess_colors
from src.svg_postprocess import simplify_svg_colors
from src.vectorize import preprocess_image
from tools.backend_probe.inspect import probe
from tools.fringe_experiment import fringe_metrics, trace
from tools.geometry_experiment import read_labels, render
from tools.geometry_fixtures import PALETTE, SCENES, reference_svg
from tools.geometry_metrics import geometry_metrics, palette_labels, path_complexity


def run(output, node, wasm, seam_only=False):
    # WASI paths are relative to the repository preopen, not Windows drive paths.
    output.mkdir(parents=True, exist_ok=False)
    cases, jobs = [], []
    for scene in (["seam"] if seam_only else SCENES):
        for size in (96, 192, 384):
            for phase in (0., .5):
                directory = output / f"{scene}-{size}-phase{phase:g}"
                directory.mkdir()
                source = directory / "reference.svg"
                source.write_text(reference_svg(scene, size, phase), encoding="utf-8")
                for filename, scale in (("input.png", 1), ("reference.png", 4)):
                    jobs.append(dict(input=str(source.resolve()), output=str((directory / filename).resolve()), scale=scale))
                cases.append((scene, size, phase, directory))
    renderer = render(node, output, "references", jobs)
    rows, jobs = [], []
    for scene, size, phase, directory in cases:
        prep = preprocess_colors(directory / "input.png", directory / "prepared.png")
        image = preprocess_image(directory / "prepared.png")
        rgba = directory / "input.rgba"
        rgba.write_bytes(image.tobytes())
        native = trace(image, prep["filter_speckle"])
        (directory / "native.svg").write_text(native, encoding="utf-8")
        variants = {}
        for name, patch in (("control", ""), ("solid", "solid-neighbour"), ("contact", "boundary-contact")):
            stem = directory / name
            raw = probe(node, wasm, rgba, image.size, prep["filter_speckle"], stem, patch,
                        round(size * 40 / 192) * size + round(size * 20 / 192) if scene == "seam" else None)
            if name == "control" and stem.with_suffix(".svg").read_bytes() != native.encode("utf-8"):
                raise AssertionError(f"Rust control differs from installed VTracer: {directory}")
            final, delta = simplify_svg_colors(raw)
            path = directory / f"{name}-final.svg"
            path.write_text(final, encoding="utf-8")
            segmented = Image.frombytes("RGBA", image.size, stem.with_suffix(".rgba").read_bytes())
            segmented.save(directory / f"{name}-segmented.png")
            variants[name] = dict(delta_e=delta, bytes=len(final.encode()), **path_complexity(final),
                                  raw_equals_final=raw == final)
            if scene == "seam":
                variants[name]["segmented_fringe"] = fringe_metrics(
                    palette_labels(np.asarray(segmented.convert("RGB")), PALETTE), size, phase, 1)
            jobs.append(dict(input=str(path.resolve()), output=str((directory / f"{name}-final.png").resolve()), scale=4))
        rows.append(dict(case=directory.name, scene=scene, size=size, phase=phase,
                         native_equals_control=True, preprocessing=prep, variants=variants))
        print("Traced", directory.name, flush=True)
    render(node, output, "traces", jobs)
    for row in rows:
        directory = output / row["case"]
        reference = read_labels(directory / "reference.png")
        for name, stats in row["variants"].items():
            actual = read_labels(directory / f"{name}-final.png")
            stats.update(geometry_metrics(reference, actual, 4))
            if row["scene"] == "seam":
                stats["fringe"] = fringe_metrics(actual, row["size"], row["phase"], 4)
            stats["local"] = {}
            for region, box in SCENES[row["scene"]]["regions"].items():
                left, top, right, bottom = [round((v * row["size"] / 192 + row["phase"]) * 4) for v in box]
                ref_roi, act_roi = reference[top:bottom, left:right], actual[top:bottom, left:right]
                stats["local"][region] = dict(
                    mismatch_area_px=float(np.count_nonzero(ref_roi != act_roi) / 16),
                    uncovered_area_px=float(np.count_nonzero((ref_roi != 0) & (act_roi == 0)) / 16))
        print("Measured", row["case"], {k: round(v["mismatch_area_px"], 3) for k, v in row["variants"].items()}, flush=True)
    result = dict(versions={n: version(n) for n in ("vtracer", "Pillow", "numpy", "opencv-python-headless")},
                  renderer=renderer, wasm_sha256=hashlib.sha256(wasm.read_bytes()).hexdigest(),
                  render_scale=4, rows=rows)
    (output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--seam-only", action="store_true")
    args = parser.parse_args()
    run(args.output, args.node, args.wasm, args.seam_only)
