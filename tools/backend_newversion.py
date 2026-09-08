"""Run the isolated VTracer alpha on the same prepared geometry fixtures.

Start in a separate Python process with the extracted alpha wheel first on
sys.path. Never import two native versions into one process.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image
import vtracer

from src.svg_postprocess import simplify_svg_colors
from tools.fringe_experiment import fringe_metrics
from tools.geometry_experiment import read_labels, render
from tools.geometry_fixtures import SCENES
from tools.geometry_metrics import geometry_metrics


def run(source, output, node):
    assert vtracer.__version__ == "1.0.0-alpha.3", vtracer.__version__
    report = json.loads((source / "report.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    rows, jobs = [], []
    for case in report["rows"]:
        directory = output / case["case"]
        directory.mkdir()
        with Image.open(source / case["case"] / "prepared.png") as original:
            image = original.convert("RGBA")
        variants = {}
        for clustering in ("color-cluster", "watershed"):
            config = vtracer.Config(clustering=clustering, hierarchical="stacked", mode="spline",
                                    filter_speckle=case["preprocessing"]["filter_speckle"],
                                    color_precision=5, layer_difference=16, corner_threshold=45,
                                    length_threshold=4., max_iterations=10, splice_threshold=45,
                                    optimize=0, simplify=None, watershed_detail=128)
            config.path_precision = None
            raw = config.convert_pixels(image.tobytes(), *image.size)
            final, delta = simplify_svg_colors(raw)
            (directory / f"{clustering}-raw.svg").write_text(raw, encoding="utf-8")
            svg = directory / f"{clustering}.svg"
            svg.write_text(final, encoding="utf-8")
            paths = [e for e in ET.fromstring(final).iter() if e.tag.endswith("}path")]
            variants[clustering] = dict(paths=len(paths), fills=sorted({e.attrib.get("fill", "") for e in paths}),
                                        bytes=len(final.encode()), delta_e=delta)
            jobs.append(dict(input=str(svg.resolve()), output=str(svg.with_suffix(".png").resolve()), scale=4))
            if case["scene"] == "seam":
                jobs.append(dict(input=str((directory / f"{clustering}-raw.svg").resolve()),
                                 output=str((directory / f"{clustering}-raw.png").resolve()), scale=4))
        rows.append({k: case[k] for k in ("case", "scene", "size", "phase")} | dict(variants=variants))
        print("Traced alpha", case["case"], flush=True)
    renderer = render(node, output, "traces", jobs)
    for row in rows:
        reference = read_labels(source / row["case"] / "reference.png")
        for name, stats in row["variants"].items():
            actual = read_labels(output / row["case"] / f"{name}.png")
            stats.update(geometry_metrics(reference, actual, 4))
            if row["scene"] == "seam":
                stats["fringe"] = fringe_metrics(actual, row["size"], row["phase"], 4)
                stats["raw_fringe"] = fringe_metrics(
                    read_labels(output / row["case"] / f"{name}-raw.png"), row["size"], row["phase"], 4)
            stats["local"] = {}
            for region, box in SCENES[row["scene"]]["regions"].items():
                left, top, right, bottom = [round((v * row["size"] / 192 + row["phase"]) * 4) for v in box]
                ref_roi, act_roi = reference[top:bottom, left:right], actual[top:bottom, left:right]
                stats["local"][region] = dict(mismatch_area_px=float(np.count_nonzero(ref_roi != act_roi) / 16),
                    uncovered_area_px=float(np.count_nonzero((ref_roi != 0) & (act_roi == 0)) / 16))
        print("Measured alpha", row["case"], flush=True)
    result = dict(version=vtracer.__version__, renderer=renderer, rows=rows,
                  source_report_sha256=hashlib.sha256((source / "report.json").read_bytes()).hexdigest(),
                  note="Both use speckle=4; watershed is a different frontend, not equivalent clustering parameters.")
    (output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node", required=True)
    args = parser.parse_args()
    run(args.source, args.output, args.node)
