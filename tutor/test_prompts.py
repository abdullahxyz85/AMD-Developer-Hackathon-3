import copy
import json
import unittest
from recommendation.recommender import get_recommendations
from .prompts import prepare_context, build_messages, validate_lesson, insufficient_lesson


def sample_context(known=None):
    # Synthetic evidence for contract tests, NOT a production rule source.
    rec = get_recommendations(known or ["Monopoly", "Chess"], "Catan").model_dump()
    rag = {"game_resolved": "Catan", "insufficient_evidence": False, "passages": [{
        "game": "Catan", "section": "objective", "layer": "curated_rules",
        "text": "The goal is to reach 10 victory points.", "score": 1,
        "source": {"title": "Synthetic test fixture", "url": ""}}]}
    return prepare_context(rec, rag, "understand the objective")


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.context = sample_context()
        self.output = {"status": "ok", "target_game": "Catan", "title": "Goal",
                       "sections": [{"text": "Reach 10 victory points.", "evidence_ids": ["p1"]}],
                       "comparisons": [], "quiz": [], "warnings": []}

    def test_valid_output(self):
        self.assertEqual(validate_lesson(json.dumps(self.output), self.context).status, "ok")

    def test_comparison_requires_both_games(self):
        self.output["comparisons"] = [{"text": "Compare resources", "evidence_ids": ["p1"],
            "familiar_game": "Monopoly", "key_difference": "Different resources"}]
        with self.assertRaisesRegex(ValueError, "both games"):
            validate_lesson(json.dumps(self.output), self.context)
        familiar = {"game_resolved": "Monopoly", "passages": [{
            "game": "Monopoly", "section": "overview", "layer": "fact_card",
            "text": "Synthetic Monopoly evidence", "score": 1,
            "source": {"title": "Test fixture", "url": ""}}]}
        rag = {"game_resolved": "Catan", "passages": list(self.context["evidence"].values())}
        context = prepare_context(self.context["recommendation"], rag, familiar_retrievals=[familiar])
        self.output["comparisons"][0]["evidence_ids"] = ["p1", "p2"]
        validate_lesson(json.dumps(self.output), context)

    def test_inline_citation_in_difference_must_be_declared(self):
        self.output["comparisons"] = [{"text": "Compare", "evidence_ids": ["p1"],
            "familiar_game": "Monopoly", "key_difference": "Difference [p6, p8]"}]
        with self.assertRaisesRegex(ValueError, "Unknown evidence ID"):
            validate_lesson(json.dumps(self.output), self.context)

    def test_valid_inline_citation_is_added_to_evidence_ids(self):
        self.output["sections"][0]["text"] = "Reach 10 victory points [p1]."
        lesson = validate_lesson(json.dumps(self.output), self.context)
        self.assertEqual(lesson.sections[0].evidence_ids, ["p1"])

    def test_familiar_evidence_does_not_replace_missing_target(self):
        familiar = {"game_resolved": "Monopoly", "passages": [{
            "game": "Monopoly", "section": "overview", "layer": "fact_card",
            "text": "Test", "score": 1, "source": {"title": "Test"}}]}
        context = prepare_context(self.context["recommendation"],
            {"game_resolved": "Catan", "passages": []}, familiar_retrievals=[familiar])
        self.assertTrue(context["insufficient_evidence"])

    def test_two_profiles_change_teaching_inputs(self):
        other = sample_context(["Poker", "Risk"])
        self.assertNotEqual(self.context["recommendation"]["per_mechanic"], other["recommendation"]["per_mechanic"])
        self.assertNotEqual(build_messages(self.context)[1], build_messages(other)[1])
        self.assertEqual(self.context["evidence"], other["evidence"])

    def test_unknown_citation_rejected(self):
        self.output["sections"][0]["evidence_ids"] = ["fake"]
        with self.assertRaises(ValueError):
            validate_lesson(json.dumps(self.output), self.context)

    def test_missing_evidence_blocks_teaching(self):
        context = copy.deepcopy(self.context)
        context["insufficient_evidence"] = True
        with self.assertRaises(ValueError):
            validate_lesson(json.dumps(self.output), context)
        validate_lesson(insufficient_lesson(context).model_dump_json(), context)

    def test_wrong_game_rejected(self):
        with self.assertRaises(ValueError):
            prepare_context(self.context["recommendation"], {"game_resolved": "Chess"})

    def test_quiz_index_rejected(self):
        self.output["quiz"] = [{"text": "Goal?", "evidence_ids": ["p1"],
                                "options": ["10", "20"], "correct_index": 2, "explanation": "10"}]
        with self.assertRaises(ValueError):
            validate_lesson(json.dumps(self.output), self.context)

    def test_unknown_familiar_game_rejected(self):
        self.output["comparisons"] = [{"text": "Comparison", "evidence_ids": ["p1"],
            "familiar_game": "Risk", "key_difference": "Different objective"}]
        with self.assertRaises(ValueError):
            validate_lesson(json.dumps(self.output), self.context)


if __name__ == "__main__":
    unittest.main()
