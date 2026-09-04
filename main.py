import argparse
from pathlib import Path

from src.preprocess import preprocess_and_vectorize


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Converte automaticamente uma imagem raster em SVG."
    )
    parser.add_argument("input_image", type=Path, help="Imagem PNG, JPG ou WEBP")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Caminho do SVG de saida (padrao: outputs/<nome>.svg)",
    )
    args = parser.parse_args()

    if not args.input_image.is_file():
        parser.error(f"Imagem nao encontrada: {args.input_image}")

    output_path = args.output or Path("outputs") / f"{args.input_image.stem}.svg"
    result_path = preprocess_and_vectorize(args.input_image, output_path)

    print(f"SVG criado em: {result_path}")


if __name__ == "__main__":
    main()
