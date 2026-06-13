import unittest
from scripts.dns_suite.core import format_safe, get_percentile

class TestDNSSuiteUtils(unittest.TestCase):
    def test_format_safe(self):
        self.assertEqual(format_safe(1234.56, 2), "1_2_3_4 . 5_6")
        self.assertEqual(format_safe(0.123, 3), "0 . 1_2_3")
        self.assertEqual(format_safe(100), "1_0_0 . 0_0")

    def test_get_percentile(self):
        data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        self.assertEqual(get_percentile(data, 50), 60.0) # Median
        self.assertEqual(get_percentile(data, 90), 100.0) # P90
        self.assertEqual(get_percentile(data, 10), 20.0) # P10
        self.assertEqual(get_percentile([], 50), 0.0)

if __name__ == '__main__':
    unittest.main()
