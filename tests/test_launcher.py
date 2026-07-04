from __future__ import annotations

import sys
import unittest

import run


class LauncherTests(unittest.TestCase):
    def test_build_icon_image_size(self) -> None:
        image = run.build_icon_image(32)
        self.assertEqual(image.size, (32, 32))

    def test_ensure_standard_streams_recovers_missing_streams(self) -> None:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        try:
            sys.stdout = None
            sys.stderr = None
            run.ensure_standard_streams()
            self.assertIsNotNone(sys.stdout)
            self.assertIsNotNone(sys.stderr)
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


if __name__ == "__main__":
    unittest.main()
