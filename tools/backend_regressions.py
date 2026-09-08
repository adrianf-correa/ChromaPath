"""Re-run the twelve existing cases; alpha mode must run in its own process."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
import vtracer

from src.comparison import compare_vectorizations
from src.preprocess import preprocess_colors
from src.svg_analysis import analyze_svg
from src.svg_postprocess import simplify_svg_colors
from src.vectorize import preprocess_image
from tools.geometry_experiment import render


def run(baseline, output, node, control=None):
    reports = json.loads(baseline.read_text())["reports"]
    output.mkdir(parents=True, exist_ok=False)
    rows, jobs = [], []
    for filename, previous in reports.items():
        source = Path(filename)
        directory = output / source.stem
        directory.mkdir()
        prepared = directory / "prepared.png"
        prep = preprocess_colors(source, prepared)
        variants = {}
        if control is None:
            result = compare_vectorizations(source, directory)
            for stage, info in result.items():
                assert info["path"].read_bytes() == Path(previous[stage]["path"]).read_bytes(), (filename, stage)
            path = result["chromapath"]["path"]
            variants["control"] = dict(**analyze_svg(path), svg=str(path),
                                       sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        else:
            assert vtracer.__version__ == "1.0.0-alpha.3"
            image = preprocess_image(prepared)
            for clustering in ("color-cluster", "watershed"):
                config = vtracer.Config(clustering=clustering, filter_speckle=prep["filter_speckle"],
                                        color_precision=5, corner_threshold=45, optimize=0,
                                        hierarchical="stacked", mode="spline", layer_difference=16,
                                        length_threshold=4., max_iterations=10, splice_threshold=45,
                                        simplify=None, watershed_detail=128)
                config.path_precision = None
                svg = simplify_svg_colors(config.convert_pixels(image.tobytes(), *image.size))[0]
                path = directory / f"{clustering}.svg"
                path.write_text(svg, encoding="utf-8")
                variants[clustering] = dict(**analyze_svg(path), svg=str(path),
                                           sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        for name, stats in variants.items():
            jobs.append(dict(input=str(Path(stats["svg"]).resolve()),
                             output=str((directory / f"{name}.png").resolve()), scale=1))
        rows.append(dict(case=source.stem, input=str(source), preprocessing=prep, variants=variants))
        print("Compared", source.stem, {k:(v["paths"],v["colors"]) for k,v in variants.items()}, flush=True)
    renderer = render(node, output, "traces", jobs)
    if control:
        for row in rows:
            with Image.open(control / row["case"] / "control.png") as image:
                reference = np.asarray(image.convert("RGB"), dtype=np.int16)
            for name, stats in row["variants"].items():
                with Image.open(output / row["case"] / f"{name}.png") as image:
                    actual = np.asarray(image.convert("RGB"), dtype=np.int16)
                delta = np.abs(reference - actual)
                stats["render_equals_control"] = bool(np.array_equal(reference, actual))
                stats["changed_pixels_rgb_gt8"] = int(np.count_nonzero(delta.max(axis=2) > 8))
                stats["mean_channel_difference"] = float(delta.mean())
    result = dict(rows=rows, renderer=renderer, production_stages_identical=36 if control is None else None,
                  note="Real-image differences measure change, not fidelity; no vector ground truth for local samples.")
    (output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--control", type=Path)
    args = parser.parse_args()
    run(args.baseline, args.output, args.node, args.control)
