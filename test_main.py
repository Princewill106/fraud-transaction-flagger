import unittest

import main


class FraudTests(unittest.TestCase):
    def test_decisions(self):
        r = main.run(main.load("sample_history.csv"), main.load("sample_incoming.csv"))
        d = [x["decision"] for x in r]
        self.assertEqual(d[0], "ALLOW")
        self.assertEqual(d[1], "ALLOW")
        self.assertEqual(d[2], "BLOCK")
        self.assertEqual(d[5], "BLOCK")


if __name__ == "__main__":
    unittest.main()
