import unittest
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from retry import get_backoff_delay

class TestRetry(unittest.TestCase):
    def test_get_backoff_delay(self):
        # 1. Edge cases (0 or negative attempts)
        self.assertEqual(get_backoff_delay(0, 2.0), 0.0)
        self.assertEqual(get_backoff_delay(-5, 2.0), 0.0)

        # 2. Base 2.0 calculations
        self.assertEqual(get_backoff_delay(1, 2.0), 1.0)
        self.assertEqual(get_backoff_delay(2, 2.0), 2.0)
        self.assertEqual(get_backoff_delay(3, 2.0), 4.0)
        self.assertEqual(get_backoff_delay(4, 2.0), 8.0)

        # 3. Base 3.0 calculations
        self.assertEqual(get_backoff_delay(1, 3.0), 1.0)
        self.assertEqual(get_backoff_delay(2, 3.0), 3.0)
        self.assertEqual(get_backoff_delay(3, 3.0), 9.0)

if __name__ == "__main__":
    unittest.main()
