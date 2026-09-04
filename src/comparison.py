import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from src.preprocess import preprocess_colors
from src.svg_analysis import analyze_svg
from src.svg_postprocess import estimate_adaptive_color_threshold
from src.vectorize import vectorize_image


def compare_vectorizations(
    input_path: Path,
    output_directory: Path = Path("outputs/comparisons"),
) -> dict:
    """Gera e analisa as etapas baseline, preparada e final."""
    output_directory.mkdir(parents=True, exist_ok=True)

    baseline_path = output_directory / f"{input_path.stem}-baseline.svg"
    prepared_path = output_directory / f"{input_path.stem}-prepared.svg"
    chromapath_path = output_directory / f"{input_path.stem}-chromapath.svg"

    vectorize_image(
        input_path,
        baseline_path,
        simplify_colors=False,
    )

    with TemporaryDirectory(
        prefix="chromapath-comparison-"
    ) as temporary_directory:
        prepared_image = Path(temporary_directory) / "prepared.png"
        preprocessing_report = preprocess_colors(
            input_path,
            prepared_image,
        )
        filter_speckle = preprocessing_report["filter_speckle"]

        vectorize_image(
            prepared_image,
            prepared_path,
            simplify_colors=False,
            filter_speckle=filter_speckle,
        )
        prepared_svg = prepared_path.read_text(encoding="utf-8")
        adaptive_delta_e = estimate_adaptive_color_threshold(prepared_svg)

        vectorize_image(
            prepared_image,
            chromapath_path,
            simplify_colors=True,
            filter_speckle=filter_speckle,
        )

    return {
        "baseline": {
            "path": baseline_path,
            **analyze_svg(baseline_path),
        },
        "prepared": {
            "path": prepared_path,
            **analyze_svg(prepared_path),
        },
        "chromapath": {
            "path": chromapath_path,
            "delta_e": adaptive_delta_e,
            **analyze_svg(chromapath_path),
        },
    }


def format_bytes(size: int) -> str:
    """Formata bytes de maneira mais fácil de ler."""
    if size < 1024:
        return f"{size} B"
    return f"{size / 1024:.1f} KB"


def print_comparison(report: dict) -> None:
    """Exibe as métricas das etapas comparadas no terminal."""
    print("\nComparação concluída:\n")
    print(f"{'Versão':<12} {'Caminhos':>9} {'Cores':>7} {'Tamanho':>10}")
    print("-" * 42)

    labels = {
        "baseline": "Baseline",
        "prepared": "Preparado",
        "chromapath": "ChromaPath",
    }

    for name, metrics in report.items():
        label = labels[name]
        print(
            f"{label:<12} "
            f"{metrics['paths']:>9} "
            f"{metrics['colors']:>7} "
            f"{format_bytes(metrics['bytes']):>10}"
        )

    print(f"\nDelta E adaptativo: {report['chromapath']['delta_e']:.1f}")

    print("\nArquivos gerados:")
    for name, metrics in report.items():
        print(f"{labels[name]:<10}: {metrics['path']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara o VTracer direto com o pipeline do ChromaPath."
    )
    parser.add_argument(
        "input_image",
        type=Path,
        help="Imagem PNG, JPG ou WEBP que será comparada",
    )
    args = parser.parse_args()

    if not args.input_image.is_file():
        parser.error(f"Imagem não encontrada: {args.input_image}")

    report = compare_vectorizations(args.input_image)
    print_comparison(report)


if __name__ == "__main__":
    main()
