import argparse
from pathlib import Path

from src.preprocess import preprocess_and_vectorize
from src.svg_analysis import analyze_svg
from src.vectorize import vectorize_image


def compare_vectorizations(
    input_path: Path,
    output_directory: Path = Path("outputs/comparisons"),
) -> dict:
    """Gera e analisa as versões baseline e ChromaPath de uma imagem."""
    output_directory.mkdir(parents=True, exist_ok=True)

    baseline_path = output_directory / f"{input_path.stem}-baseline.svg"
    chromapath_path = output_directory / f"{input_path.stem}-chromapath.svg"

    vectorize_image(
        input_path,
        baseline_path,
        simplify_colors=False,
    )
    preprocess_and_vectorize(
        input_path,
        chromapath_path,
    )

    return {
        "baseline": {
            "path": baseline_path,
            **analyze_svg(baseline_path),
        },
        "chromapath": {
            "path": chromapath_path,
            **analyze_svg(chromapath_path),
        },
    }


def format_bytes(size: int) -> str:
    """Formata bytes de maneira mais fácil de ler."""
    if size < 1024:
        return f"{size} B"
    return f"{size / 1024:.1f} KB"


def print_comparison(report: dict) -> None:
    """Exibe as métricas das duas versões no terminal."""
    print("\nComparação concluída:\n")
    print(f"{'Versão':<12} {'Caminhos':>9} {'Cores':>7} {'Tamanho':>10}")
    print("-" * 42)

    for name, metrics in report.items():
        label = "Baseline" if name == "baseline" else "ChromaPath"
        print(
            f"{label:<12} "
            f"{metrics['paths']:>9} "
            f"{metrics['colors']:>7} "
            f"{format_bytes(metrics['bytes']):>10}"
        )

    print("\nArquivos gerados:")
    print(f"Baseline:   {report['baseline']['path']}")
    print(f"ChromaPath: {report['chromapath']['path']}")


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
