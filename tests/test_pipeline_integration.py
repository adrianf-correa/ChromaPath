import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.preprocess import preprocess_colors
from src.svg_analysis import analyze_svg
from src.vectorize import vectorize_image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT_ROOT / "samples" / "fixtures"


class PipelineFixtureTests(unittest.TestCase):
    def test_noisy_robot_converges_to_clean_result(self) -> None:
        with TemporaryDirectory(prefix="chromapath-integration-") as directory:
            temporary_root = Path(directory)
            results = {}

            for name in ("clean", "noisy"):
                prepared_path = temporary_root / f"robot-{name}-prepared.png"
                svg_path = temporary_root / f"robot-{name}.svg"
                report = preprocess_colors(
                    FIXTURES / f"robot-{name}.png",
                    prepared_path,
                )
                vectorize_image(
                    prepared_path,
                    svg_path,
                    filter_speckle=report["filter_speckle"],
                )
                results[name] = {
                    "report": report,
                    "svg": analyze_svg(svg_path),
                }

        clean = results["clean"]
        noisy = results["noisy"]

        self.assertEqual(clean["svg"]["paths"], 17)
        self.assertEqual(clean["svg"]["colors"], 5)
        self.assertEqual(noisy["svg"]["paths"], clean["svg"]["paths"])
        self.assertEqual(noisy["svg"]["colors"], clean["svg"]["colors"])
        self.assertEqual(
            clean["report"]["isolated_cleanup"]["removed_components"],
            0,
        )
        self.assertGreaterEqual(
            noisy["report"]["isolated_cleanup"]["removed_components"],
            8,
        )
        self.assertGreater(
            noisy["report"]["isolated_cleanup"]["removed_protrusions"],
            0,
        )
        self.assertEqual(clean["report"]["filter_speckle"], 4)
        self.assertEqual(noisy["report"]["filter_speckle"], 32)

    def test_repeated_detached_details_survive_noise_cleanup(self) -> None:
        with TemporaryDirectory(prefix="chromapath-details-") as directory:
            temporary_root = Path(directory)
            results = {}

            for name in ("clean", "noisy"):
                prepared_path = temporary_root / f"details-{name}-prepared.png"
                svg_path = temporary_root / f"details-{name}.svg"
                report = preprocess_colors(
                    FIXTURES / f"detached-details-{name}.png",
                    prepared_path,
                )
                vectorize_image(
                    prepared_path,
                    svg_path,
                    filter_speckle=report["filter_speckle"],
                )
                results[name] = {
                    "report": report,
                    "svg": analyze_svg(svg_path),
                }

        clean = results["clean"]
        noisy = results["noisy"]

        self.assertEqual(clean["svg"]["paths"], 11)
        self.assertEqual(clean["svg"]["colors"], 5)
        self.assertEqual(noisy["svg"]["paths"], clean["svg"]["paths"])
        self.assertEqual(noisy["svg"]["colors"], clean["svg"]["colors"])
        self.assertEqual(
            clean["report"]["isolated_cleanup"]["protected_repeated_details"],
            3,
        )
        self.assertEqual(
            noisy["report"]["isolated_cleanup"]["protected_repeated_details"],
            3,
        )
        self.assertGreaterEqual(
            noisy["report"]["isolated_cleanup"]["removed_components"],
            8,
        )
        self.assertEqual(noisy["report"]["filter_speckle"], 4)

    def test_unique_irregular_detail_survives_noise_cleanup(self) -> None:
        with TemporaryDirectory(prefix="chromapath-unique-") as directory:
            temporary_root = Path(directory)
            results = {}

            for name in ("clean", "noisy"):
                prepared_path = temporary_root / f"unique-{name}-prepared.png"
                svg_path = temporary_root / f"unique-{name}.svg"
                report = preprocess_colors(
                    FIXTURES / f"unique-detail-{name}.png",
                    prepared_path,
                )
                vectorize_image(
                    prepared_path,
                    svg_path,
                    filter_speckle=report["filter_speckle"],
                )
                results[name] = {
                    "report": report,
                    "svg": analyze_svg(svg_path),
                    "bytes": svg_path.read_bytes(),
                }

        clean = results["clean"]
        noisy = results["noisy"]

        self.assertEqual(clean["svg"]["paths"], 9)
        self.assertEqual(clean["svg"]["colors"], 4)
        self.assertEqual(noisy["svg"]["paths"], clean["svg"]["paths"])
        self.assertEqual(noisy["svg"]["colors"], clean["svg"]["colors"])
        self.assertEqual(noisy["bytes"], clean["bytes"])
        self.assertEqual(
            clean["report"]["isolated_cleanup"]["protected_unique_details"],
            1,
        )
        self.assertEqual(
            noisy["report"]["isolated_cleanup"]["protected_unique_details"],
            1,
        )
        self.assertGreaterEqual(
            noisy["report"]["isolated_cleanup"]["removed_components"],
            8,
        )
        self.assertEqual(noisy["report"]["filter_speckle"], 4)


if __name__ == "__main__":
    unittest.main()
