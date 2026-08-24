import unittest

from app.tools.planning.intent import (
    is_retirement_health_check_intent,
    normalize_intent_text,
)


class TestNormalizeIntentText(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(normalize_intent_text("RETIREMENT"), "retirement")

    def test_collapses_whitespace(self):
        self.assertEqual(
            normalize_intent_text("retirement   health\tcheck"),
            "retirement health check",
        )

    def test_trims(self):
        self.assertEqual(normalize_intent_text("  retirement  "), "retirement")


class TestIsRetirementHealthCheckIntent(unittest.TestCase):
    def test_matches_documented_examples(self):
        examples = (
            "Run retirement planning health check.",
            "retirement planning health check",
            "retirement health check diagnostic",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertTrue(is_retirement_health_check_intent(text))

    def test_matches_case_and_whitespace_variants(self):
        self.assertTrue(
            is_retirement_health_check_intent("  RUN   Retirement   Health CHECK  ")
        )

    def test_does_not_match_unrelated_text(self):
        self.assertFalse(is_retirement_health_check_intent("what is a glide path?"))
        self.assertFalse(is_retirement_health_check_intent("check my order status"))

    def test_empty_text_does_not_match(self):
        self.assertFalse(is_retirement_health_check_intent(""))
        self.assertFalse(is_retirement_health_check_intent("   "))


if __name__ == "__main__":
    unittest.main()
