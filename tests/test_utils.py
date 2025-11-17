import unittest
from utils import format_duration

class TestUtils(unittest.TestCase):

    def test_format_duration(self):
        self.assertEqual(format_duration(None), "")
        self.assertEqual(format_duration("invalid"), "Invalido")
        self.assertEqual(format_duration(65.5), "00:01:05.50")
        self.assertEqual(format_duration(3600), "01:00:00.00")

if __name__ == '__main__':
    unittest.main()
