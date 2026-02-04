#!/usr/bin/env python3
"""
Test file for KameleonS
"""

import unittest
from main import main

class TestKameleonS(unittest.TestCase):
    def test_main_exists(self):
        """Test that main function exists"""
        self.assertTrue(callable(main))

if __name__ == '__main__':
    unittest.main()