import tempfile
import unittest
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
    import optimize_covers
except ImportError:
    optimize_covers = None


@unittest.skipUnless(optimize_covers, "Install Pillow to test cover optimization")
class CoverOptimizationTests(unittest.TestCase):
    def test_variants_preserve_proportions_transparency_and_small_sources(self):
        for dimensions in [(900, 1200), (150, 200)]:
            with self.subTest(dimensions=dimensions), tempfile.TemporaryDirectory() as temp:
                source = Image.new("RGBA", dimensions, (80, 140, 200, 128))
                payload = BytesIO()
                source.save(payload, "PNG")
                result = optimize_covers.create_variants(payload.getvalue(), Path(temp))
                self.assertTrue(result["variants"])
                for variant in result["variants"]:
                    with Image.open(Path(temp) / variant["src"]) as image:
                        self.assertEqual(image.format, "WEBP")
                        self.assertEqual(image.size, (variant["width"], variant["height"]))
                        self.assertLessEqual(image.width, dimensions[0])
                        self.assertAlmostEqual(image.width / image.height, 0.75, places=2)
                        self.assertEqual(image.getpixel((0, 0))[3], 128)
                        self.assertNotIn("exif", image.info)


if __name__ == "__main__":
    unittest.main()
