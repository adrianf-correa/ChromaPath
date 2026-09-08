"""Geometric acceptance check for a rendered seam fixture, not an SVG counter.

Example: python -m tools.check_backend_fringe result.png --size 192 --phase .5
The current backend exits 1; a candidate without foreign coral exits 0.
This single-issue check does NOT certify silhouette, color or detail fidelity.
"""
import argparse
import json

import numpy as np

from tools.fringe_experiment import fringe_metrics
from tools.geometry_experiment import read_labels


def assert_no_foreign_fringe(labels, size, phase, scale=4):
    metrics = fringe_metrics(labels, size, phase, scale)
    # A blank image, or deletion/repainting of either major shape, cannot pass.
    for label in (1, 2):
        if np.count_nonzero(labels == label) < labels.size * .1:
            raise AssertionError(f"Main region {label} is missing or severely reduced")
    area = sum(value["foreign_area_px"] for value in metrics.values())
    if area > 0:
        raise AssertionError(f"Foreign coral occupies {area:g} input-pixel squared in external ROIs")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png")
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--phase", type=float, required=True)
    parser.add_argument("--scale", type=int, default=4)
    args = parser.parse_args()
    try:
        result = assert_no_foreign_fringe(read_labels(args.png), args.size, args.phase, args.scale)
    except AssertionError as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS:", json.dumps(result))
