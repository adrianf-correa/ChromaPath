"""Small command-line runner for the isolated, instrumented Rust binary."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def probe(node, wasm, rgba, size, speckle, output, patch="", watch=None):
    def wasi_path(path):
        # Node reads the wasm on the host; file arguments belong to the single
        # WASI preopen. Also accept absolute paths inside this repository.
        return Path(path).resolve().relative_to(Path.cwd().resolve()).as_posix()

    env = {k: v for k, v in os.environ.items() if not k.startswith("CHROMAPATH_")}
    if patch:
        env["CHROMAPATH_PATCH"] = patch
    if watch is not None:
        env.update(CHROMAPATH_PROBE_LOG="1", CHROMAPATH_WATCH=str(watch))
    result = subprocess.run([
        node, "--disable-warning=ExperimentalWarning",
        str(Path(__file__).with_name("run.cjs")), str(wasm), wasi_path(rgba),
        str(size[0]), str(size[1]), str(speckle), wasi_path(output.with_suffix(".svg")),
        wasi_path(output.with_suffix(".rgba")),
    ], env=env, capture_output=True, text=True, check=True)
    if watch is not None:
        output.with_suffix(".jsonl").write_text(result.stderr, encoding="utf-8")
    return output.with_suffix(".svg").read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--size", type=int, nargs=2, required=True)
    parser.add_argument("--speckle", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--patch", default="")
    parser.add_argument("--watch", type=int)
    args = parser.parse_args()
    probe(args.node, args.wasm, args.input, args.size, args.speckle,
          args.output, args.patch, args.watch)
    if args.watch is not None:
        for line in args.output.with_suffix(".jsonl").read_text().splitlines():
            event = json.loads(line)
            if event.get("watch_from") or event.get("event") == "output":
                print(json.dumps(event))


if __name__ == "__main__":
    main()
