import unittest
from unittest.mock import patch
from server import animation


def fixture(target):
    lesson = {"target_game": target, "title": "First turn", "sections": [
        {"text": "Choose a token."}, {"text": "Roll and move."}]}
    rec = {"target_game": target, "player_known_games": ["Chess"],
           "per_mechanic": [{"mechanic": "dice_rolling"}]}
    return lesson, rec


class GameSceneTests(unittest.TestCase):
    def test_monopoly_fallback_is_not_catan(self):
        plan = animation.fallback_plan(*fixture("Monopoly"))
        self.assertEqual(plan["scene_type"], "step_cards")
        self.assertTrue(all(not step["highlight"] for step in plan["steps"]))

    def test_catan_keeps_production_scene(self):
        self.assertEqual(animation.fallback_plan(*fixture("Catan"))["scene_type"], "dice_production")

    def test_wrong_llm_scene_becomes_neutral_cards(self):
        wrong = animation.fallback_plan(*fixture("Catan"))
        with patch("server.llm.chat", return_value=wrong):
            plan, origin = animation.generate_plan(*fixture("Monopoly"), "beginner")
        self.assertEqual(origin, "llm")
        self.assertEqual(plan["scene_type"], "step_cards")
        self.assertEqual(plan["steps"][0]["caption"], wrong["steps"][0]["caption"])
        self.assertTrue(all(not step["highlight"] for step in plan["steps"]))

    def test_model_failure_still_uses_correct_game(self):
        with patch("server.llm.chat", side_effect=RuntimeError("offline")):
            plan, origin = animation.generate_plan(*fixture("Monopoly"), "beginner")
        self.assertEqual((plan["scene_type"], origin), ("step_cards", "fallback"))
