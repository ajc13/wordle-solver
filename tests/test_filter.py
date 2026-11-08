"""Tests for feedback filtering, response parsing and log paths.

Run with:  python3 -m unittest discover -s tests
"""

import random
import sys
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wordle_solver import (  # noqa: E402
    filter_word_list,
    log_path_for,
    parse_response,
    word_matches_feedback,
)


def reference_feedback(answer, guess):
    """NYT Wordle scoring: greens first, then yellows left-to-right by count."""
    result = ["?"] * len(guess)
    unmatched = Counter()
    for i, (a, g) in enumerate(zip(answer, guess)):
        if a == g:
            result[i] = "G"
        else:
            unmatched[a] += 1
    for i, g in enumerate(guess):
        if result[i] != "G" and unmatched[g] > 0:
            result[i] = "Y"
            unmatched[g] -= 1
    return "".join(result)


class WordMatchesFeedbackTests(unittest.TestCase):
    def test_game_2026_10_20_keeps_answer(self):
        # arose ?G?GY -> dress ?GGG? -> crest ?GGGG -> wrest
        # Pre-1.0.3 code dropped to 0 words after "dress".
        for guess, feedback in [
            ("arose", "?G?GY"),
            ("dress", "?GGG?"),
            ("crest", "?GGGG"),
        ]:
            self.assertTrue(word_matches_feedback("wrest", guess, feedback), guess)

    def test_game_2026_10_20_filter_sequence(self):
        words = ["wrest", "crest", "dress", "fresh", "prest", "trest", "press"]
        words = filter_word_list(words, "dress", "?GGG?")
        self.assertEqual(sorted(words), ["crest", "fresh", "prest", "trest", "wrest"])
        words = filter_word_list(words, "crest", "?GGGG")
        self.assertEqual(sorted(words), ["prest", "trest", "wrest"])

    def test_gray_rejects_letter_at_same_position(self):
        # speed vs answer abide -> ??Y?Y. "idler" has its only e where the
        # gray e was, so Wordle would have shown green there.
        self.assertEqual(reference_feedback("abide", "speed"), "??Y?Y")
        self.assertFalse(word_matches_feedback("idler", "speed", "??Y?Y"))
        self.assertTrue(word_matches_feedback("abide", "speed", "??Y?Y"))

    def test_duplicate_letter_gray_after_green(self):
        # Guess "undid" against answer "under": the answer has one d,
        # already green, so the second d is gray. That must not remove
        # words containing d.
        self.assertEqual(reference_feedback("under", "undid"), "GGG??")
        self.assertTrue(word_matches_feedback("under", "undid", "GGG??"))
        self.assertTrue(word_matches_feedback("undue", "undid", "GGG??"))
        self.assertFalse(word_matches_feedback("undid", "undid", "GGG??"))

    def test_matches_reference_scorer(self):
        # Small alphabet forces lots of repeated letters.
        rng = random.Random(1)
        alphabet = "abcde"

        def rand_word():
            return "".join(rng.choice(alphabet) for _ in range(5))

        for _ in range(50_000):
            answer, guess, candidate = rand_word(), rand_word(), rand_word()
            feedback = reference_feedback(answer, guess)
            expected = reference_feedback(candidate, guess) == feedback
            self.assertEqual(
                word_matches_feedback(candidate, guess, feedback),
                expected,
                f"candidate={candidate} guess={guess} feedback={feedback}",
            )


class ParseResponseTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_response("g.y??"), "G?Y??")
        self.assertEqual(parse_response(" GGGGG "), "GGGGG")

    def test_invalid(self):
        self.assertIsNone(parse_response("GGGG"))
        self.assertIsNone(parse_response("GGGGX"))


class LogPathTests(unittest.TestCase):
    def test_week_starts_monday(self):
        path = log_path_for(datetime(2026, 11, 7, 12, 0))  # Saturday
        self.assertEqual(path.parts[-3:], ("2026", "11", "wordle_solver_2026-11-02.log"))

    def test_week_spanning_months_stays_in_monday_folder(self):
        path = log_path_for(datetime(2026, 12, 3))  # Thursday; Monday is Nov 30
        self.assertEqual(path.parts[-3:], ("2026", "11", "wordle_solver_2026-11-30.log"))

    def test_week_spanning_years(self):
        path = log_path_for(datetime(2027, 1, 1))  # Friday; Monday is Dec 28
        self.assertEqual(path.parts[-3:], ("2026", "12", "wordle_solver_2026-12-28.log"))


if __name__ == "__main__":
    unittest.main()
