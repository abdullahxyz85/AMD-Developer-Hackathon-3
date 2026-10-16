"""Manim scene templates for validated animation plans.

The LLM never writes code that reaches this module: it only supplies data
(scene_type, title, steps) that has already passed server.animation.validate_plan.
Each scene_type is a fixed template that knows a small set of named objects;
a step's `highlight` ids refer to those objects.

Renders a plan with:
    python -m manim render -ql server/_render_job.py PlanScene
(the temporary job file is created by server.renderer.render).
"""
from __future__ import annotations

import textwrap

from manim import (BLACK, BLUE, BLUE_E, DOWN, FadeIn, GREEN, GREY, LEFT, LIGHT_GREY, MAROON_E,
                   ORANGE, PURPLE, RIGHT, RED, RegularPolygon, Scene, Square, TEAL, UP, VGroup,
                   YELLOW, RoundedRectangle, Circle, Create, Dot, FadeOut, Group, Indicate, Line,
                   Write, Text)

# ── palette ─────────────────────────────────────────────────────────────────
INK = "#2B2B2B"
PAPER = "#F7F3E8"
ACCENT = "#E8A33D"
DIM = "#8A8A8A"

FONT_SIZE_TITLE = 34
FONT_SIZE_CAPTION = 24
FONT_SIZE_LABEL = 20
WRAP_CAPTION = 46
WRAP_TITLE = 40


def _wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(str(text), width))


class AnimationPlanScene(Scene):
    """Base scene: title banner + caption bar + per-step highlighting."""

    def perform(self, plan: dict) -> None:
        self.stage: Group = Group()
        self.title_banner(plan.get("title", ""))
        objects = self.build_stage(plan.get("scene_type", "step_cards"))
        if objects is None:  # step_cards builds its own flow
            return
        self.play(FadeIn(self.stage), run_time=0.8)
        for step in plan.get("steps", []):
            self.play_step(step, objects)
        self.wait(0.6)
        self.play(FadeOut(self.stage), FadeOut(self.caption_mob), FadeOut(self.title_mob), run_time=0.8)

    # ── shared chrome ───────────────────────────────────────────────────
    def title_banner(self, title: str) -> None:
        self.title_mob = Text(_wrap(title, WRAP_TITLE), font_size=FONT_SIZE_TITLE, color=INK,
                              weight="BOLD").to_edge(UP, buff=0.35)
        underline = Line(LEFT * 4, RIGHT * 4, color=ACCENT, stroke_width=3).next_to(self.title_mob, DOWN, buff=0.15)
        self.play(Write(self.title_mob), Create(underline), run_time=0.9)
        self.title_mob = VGroup(self.title_mob, underline)

    def make_caption(self, text: str):
        mob = Text(_wrap(text, WRAP_CAPTION), font_size=FONT_SIZE_CAPTION, color=INK)
        bar = RoundedRectangle(corner_radius=0.15, width=12.6,
                               height=max(1.0, 0.42 * (mob.height / 1.6) + 0.45),
                               fill_color=PAPER, fill_opacity=0.95, stroke_color=ACCENT,
                               stroke_width=2)
        mob.next_to(bar.get_center(), DOWN, buff=0).set_z_index(2)
        return VGroup(bar, mob).to_edge(DOWN, buff=0.3)

    def play_step(self, step: dict, objects: dict) -> None:
        caption = self.make_caption(step.get("caption", ""))
        if not hasattr(self, "caption_mob"):
            self.caption_mob = caption
            self.play(Create(self.caption_mob), run_time=0.5)
        else:
            self.play(FadeOut(self.caption_mob, run_time=0.001), Create(caption), run_time=0.35)
            self.caption_mob = caption
        ids = set(step.get("highlight", []))
        anims = []
        for oid, mob in objects.items():
            if oid in ids:
                anims.append(Indicate(mob, color=YELLOW, scale_factor=1.12))
            else:
                anims.append(mob.animate.set_opacity(0.30))
        if anims:
            self.play(*anims, run_time=0.7)
        restore = [m.animate.set_opacity(1.0) for m in objects.values()]
        self.wait(max(0.5, float(step.get("duration", 3.0)) - 1.2))
        if restore:
            self.play(*restore, run_time=0.35)

    # ── stage builders ──────────────────────────────────────────────────
    def build_stage(self, scene_type: str):
        builders = {
            "dice_production": self.build_dice,
            "route_claim": self.build_route,
            "deck_cycle": self.build_deck,
        }
        return builders.get(scene_type, lambda: None)()

    # -- dice_production (Catan-style resource roll) ----------------------
    def build_dice(self):
        objects: dict = {}

        def hex_tile(number: str, color):
            tile = VGroup(
                RegularPolygon(n=6).scale(0.85).set_fill(color, opacity=0.85).set_stroke(INK, 3),
                Circle(radius=0.34, fill_color=PAPER, fill_opacity=1, stroke_color=INK, stroke_width=2),
                Text(number, font_size=26, color=INK, weight="BOLD").scale(0.8),
            )
            tile[2].move_to(tile[1])
            return tile

        hex8 = hex_tile("8", GREEN).move_to(LEFT * 3.2 + UP * 0.6)
        hex6 = hex_tile("6", ORANGE).move_to(RIGHT * 3.2 + UP * 0.6)
        objects["hex-8"] = hex8
        objects["hex-6"] = hex6

        def pip_die(pips: int):
            die_face = RoundedRectangle(corner_radius=0.18, width=0.95, height=0.95,
                                        fill_color=PAPER, fill_opacity=1,
                                        stroke_color=INK, stroke_width=3)
            dots = VGroup()
            positions = {1: [(0, 0)], 2: [(-0.22, 0.22), (0.22, -0.22)],
                         3: [(-0.22, 0.22), (0, 0), (0.22, -0.22)],
                         4: [(-0.22, 0.22), (0.22, 0.22), (-0.22, -0.22), (0.22, -0.22)],
                         5: [(-0.22, 0.22), (0.22, 0.22), (0, 0), (-0.22, -0.22), (0.22, -0.22)],
                         6: [(-0.22, 0.22), (0.22, 0.22), (-0.22, 0), (0.22, 0),
                             (-0.22, -0.22), (0.22, -0.22)]}[pips]
            for x, y in positions:
                dots.add(Circle(radius=0.07, fill_color=INK, fill_opacity=1, stroke_width=0)
                         .move_to(die_face.get_center() + [x, y, 0]))
            return VGroup(die_face, dots)

        dice = VGroup(pip_die(3), pip_die(5)).arrange(RIGHT, buff=0.5).move_to(UP * 0.6)
        objects["dice"] = dice

        def settlement():
            return VGroup(
                Square(side_length=0.5).set_fill(RED, opacity=0.9).set_stroke(INK, 2),
                Text("1", font_size=18, color=PAPER, weight="BOLD"),
            )

        settlements = VGroup(settlement(), settlement()).arrange(RIGHT, buff=2.6)
        settlements[0].move_to(LEFT * 3.2 + DOWN * 1.3)
        settlements[1].move_to(RIGHT * 3.2 + DOWN * 1.3)
        objects["settlements"] = settlements

        robber = VGroup(Circle(radius=0.38, fill_color=BLACK, fill_opacity=0.92, stroke_color=GREY),
                        Text("R", font_size=22, color=PAPER, weight="BOLD"))
        robber[1].move_to(robber[0])
        robber.move_to(DOWN * 1.3)
        objects["robber"] = robber
        return objects

    # -- route_claim (train route building) -------------------------------
    def build_route(self):
        objects: dict = {}
        card_colors = [RED, BLUE, GREEN, ORANGE]
        hand = VGroup(*[
            RoundedRectangle(corner_radius=0.12, width=0.9, height=1.25)
            .set_fill(color, opacity=0.9).set_stroke(INK, 2)
            for color in card_colors
        ]).arrange(RIGHT, buff=0.25).move_to(DOWN * 2.0 + LEFT * 2.5)
        objects["hand"] = hand

        city_a = Circle(radius=0.3, fill_color=INK, fill_opacity=1, stroke_width=0).move_to(LEFT * 3.4 + UP * 0.8)
        city_b = Circle(radius=0.3, fill_color=INK, fill_opacity=1, stroke_width=0).move_to(RIGHT * 3.4 + UP * 0.8)
        route = VGroup(city_a, city_b, *[
            RoundedRectangle(corner_radius=0.06, width=1.5, height=0.42)
            .set_fill(PURPLE, opacity=0.85).set_stroke(INK, 2)
            .move_to(LEFT * 1.7 + UP * 0.8 + RIGHT * 1.7 * i)
            for i in range(3)
        ])
        objects["route"] = route

        trains = VGroup(*[
            RoundedRectangle(corner_radius=0.08, width=0.7, height=0.4)
            .set_fill(TEAL, opacity=0.9).set_stroke(INK, 2)
            for _ in range(3)
        ]).arrange(DOWN, buff=0.2).move_to(RIGHT * 4.6 + DOWN * 0.2)
        objects["trains"] = trains

        score = VGroup(Text("Score", font_size=FONT_SIZE_LABEL, color=INK),
                       Text("0", font_size=40, color=ACCENT, weight="BOLD"))
        score.arrange(DOWN, buff=0.1).move_to(LEFT * 4.6 + UP * 1.6)
        objects["score"] = score
        return objects

    # -- deck_cycle (draw / play / discard loop) ---------------------------
    def build_deck(self):
        objects: dict = {}
        deck = VGroup(*[
            RoundedRectangle(corner_radius=0.1, width=1.0, height=1.4)
            .set_fill(BLUE_E, opacity=(1.0 if i == 0 else 0.75)).set_stroke(INK, 2)
            .move_to(LEFT * 4.4 + UP * 0.4 + UP * 0.06 * i)
            for i in range(4)
        ])
        deck.add(Text("DECK", font_size=18, color=PAPER, weight="BOLD").move_to(deck[0]))
        objects["deck"] = deck

        hand = VGroup(*[
            RoundedRectangle(corner_radius=0.1, width=1.0, height=1.4)
            .set_fill(GREEN, opacity=0.9).set_stroke(INK, 2)
            for _ in range(3)
        ]).arrange(RIGHT, buff=0.3).move_to(UP * 0.4)
        objects["hand"] = hand

        action = VGroup(
            RoundedRectangle(corner_radius=0.1, width=1.2, height=1.6)
            .set_fill(ACCENT, opacity=0.9).set_stroke(INK, 2),
            Text("ACTION", font_size=16, color=INK, weight="BOLD"),
        )
        action[1].move_to(action[0])
        action.move_to(RIGHT * 2.2 + UP * 0.4)
        objects["action"] = action

        supply = VGroup(*[
            RoundedRectangle(corner_radius=0.1, width=1.1, height=1.5)
            .set_fill(MAROON_E, opacity=0.9).set_stroke(INK, 2)
            for _ in range(3)
        ]).arrange(RIGHT, buff=0.25).move_to(RIGHT * 4.4 + UP * 0.4)
        objects["supply"] = supply

        discard = VGroup(*[
            RoundedRectangle(corner_radius=0.1, width=1.0, height=1.4)
            .set_fill(LIGHT_GREY, opacity=(1.0 if i == 0 else 0.6)).set_stroke(INK, 2)
            .move_to(LEFT * 4.4 + DOWN * 1.8 + UP * 0.06 * i)
            for i in range(3)
        ])
        discard.add(Text("DISCARD", font_size=16, color=INK, weight="BOLD").move_to(discard[0]))
        objects["discard"] = discard
        return objects


class StepCardsScene(AnimationPlanScene):
    """Fallback template: one teaching card per step, no game-specific art."""

    def perform(self, plan: dict) -> None:
        self.title_banner(plan.get("title", ""))
        steps = plan.get("steps", [])
        total = max(len(steps), 1)
        card_w, card_h = 10.0, 3.4
        for i, step in enumerate(steps):
            card = RoundedRectangle(corner_radius=0.25, width=card_w, height=card_h,
                                    fill_color=PAPER, fill_opacity=0.97,
                                    stroke_color=ACCENT, stroke_width=3)
            label = Text(f"{i + 1}. {_wrap(step.get('label', ''), 24)}",
                         font_size=30, color=INK, weight="BOLD").set_z_index(2)
            caption = Text(_wrap(step.get('caption', ''), 52), font_size=26,
                           color=INK).set_z_index(2)
            label.move_to(card.get_center() + UP * (card_h / 2 - 0.55))
            caption.move_to(card.get_center() + DOWN * 0.35)
            group = VGroup(card, label, caption)
            dots = VGroup(*[
                Dot(radius=0.08, fill_color=(ACCENT if j <= i else DIM), fill_opacity=1,
                    stroke_width=0)
                for j in range(total)
            ]).arrange(RIGHT, buff=0.25).to_edge(DOWN, buff=0.4)
            self.play(Create(group), Create(dots), run_time=0.7)
            self.wait(max(1.0, float(step.get("duration", 3.0)) - 0.7))
            if i < total - 1:
                self.play(FadeOut(group), FadeOut(dots), run_time=0.4)
        self.wait(0.5)
        self.play(FadeOut(VGroup(self.title_mob)), run_time=0.8)
