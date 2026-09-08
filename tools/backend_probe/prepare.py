"""Fetch SHA-pinned sources into ignored outputs; never install a Python package.

Requires Python >=3.12 and git. Run from the repository root. Existing extracted
directories are refused rather than overwritten. --cache supports offline reuse.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request
import zipfile


def prepare(root, cache, alpha=False, offline=False):
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    cache = cache.resolve() if cache else root
    cache.mkdir(parents=True, exist_ok=True)
    sources = json.loads(Path(__file__).with_name("sources.json").read_text())
    sources = {n: s for n, s in sources.items() if alpha or not s.get("alpha")}
    for spec in sources.values():
        if (root / spec["directory"]).exists():
            raise FileExistsError(f"Refusing to overwrite {root / spec['directory']}")
    for name, spec in sources.items():
        archive = cache / name
        if not archive.exists():
            if offline:
                raise FileNotFoundError(archive)
            with urllib.request.urlopen(spec["url"], timeout=60) as response:
                archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != spec["sha256"]:
            raise ValueError(f"Archive hash mismatch: {archive}")
        if name.endswith(".whl"):
            destination = root / spec["directory"]
            with zipfile.ZipFile(archive) as source:
                for entry in source.namelist():
                    if not (destination / entry).resolve().is_relative_to(destination):
                        raise ValueError(f"Unsafe wheel member: {entry}")
                source.extractall(destination)
        else:
            with tarfile.open(archive) as source:
                if any(Path(member.name).parts[0] != spec["directory"] for member in source.getmembers()):
                    raise ValueError(f"Unexpected source archive layout: {name}")
                source.extractall(root, filter="data")
        print("Verified and extracted", name)
    upstream = root / "visioncortex-0.8.10"
    patch = Path(__file__).with_name("visioncortex-0.8.10-experiment.patch").resolve()
    # --no-index lets the same small patch work outside a git worktree.
    for extra in (["--check"], []):
        subprocess.run(["git", "apply", "--no-index", *extra, str(patch)], cwd=upstream, check=True)
    print("Applied isolated instrumentation and two rejected experimental candidates")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("outputs/backend-investigation"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--alpha", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    prepare(args.root, args.cache, args.alpha, args.offline)
