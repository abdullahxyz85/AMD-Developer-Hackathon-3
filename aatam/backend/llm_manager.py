import os
import json
import re
import ast
import time
import threading
import requests
from typing import Dict, Any, Optional, List

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(PROJECT_DIR, "data", "llm_config.json")

# z.ai stays the active provider. AMD Token Factory is ready to switch on
# once the event key is pasted (or RADEON_API_KEY is set).
ZAI_PROFILE = {
    "api_base_url": "https://api.z.ai/api/paas/v4",
    "model_name": "glm-4.7-flash",
    "api_key": "",
    "temperature": 0.2,
    "max_tokens": 3000,
    "timeout_seconds": 60,
}

AMD_PROFILE = {
    "api_base_url": "https://developer.amd.com.cn/radeon/api/v1",
    "model_name": "Gemma-4-31B-IT",
    "api_key": "",
    "temperature": 0.2,
    "max_tokens": 4000,
    "timeout_seconds": 180,
}

DEFAULT_CONFIG = {
    "enabled": True,
    "provider": "zai",
    **ZAI_PROFILE,
    "providers": {
        "zai": dict(ZAI_PROFILE),
        "amd": dict(AMD_PROFILE),
    },
}

class LLMManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._config = self._load_config()
        self._apply_active()

    def _load_config(self) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        cfg = {
            "enabled": DEFAULT_CONFIG["enabled"],
            "provider": DEFAULT_CONFIG["provider"],
            **ZAI_PROFILE,
            "providers": {
                "zai": dict(ZAI_PROFILE),
                "amd": dict(AMD_PROFILE),
            },
        }
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
            except Exception as e:
                print(f"Error reading llm_config.json: {e}")
                saved = {}
            saved_providers = saved.get("providers") if isinstance(saved.get("providers"), dict) else {}
            for name in ("zai", "amd"):
                incoming = saved_providers.get(name)
                if isinstance(incoming, dict):
                    cfg["providers"][name].update(incoming)
            # Older configs stored a single endpoint. Keep that as z.ai
            # unless it was already the AMD gateway.
            if "providers" not in saved:
                flat = {k: saved[k] for k in ZAI_PROFILE if k in saved}
                url = flat.get("api_base_url", "")
                bucket = "amd" if "developer.amd.com" in url else "zai"
                cfg["providers"][bucket].update(flat)
                cfg["provider"] = saved.get("provider", bucket)
            else:
                cfg["provider"] = saved.get("provider", cfg["provider"])
            if "enabled" in saved:
                cfg["enabled"] = saved["enabled"]
        active = cfg["providers"].get(cfg["provider"], cfg["providers"]["zai"])
        cfg.update(active)
        return cfg

    def _apply_active(self) -> None:
        env_names = {"zai": "ZAI_API_KEY", "amd": "RADEON_API_KEY"}
        for name, env_name in env_names.items():
            profile = self._config["providers"].get(name) or {}
            if (profile.get("api_key") or "").strip():
                continue
            env_key = os.environ.get(env_name, "").strip()
            if env_key:
                profile["api_key"] = env_key
                self._config["providers"][name] = profile
        active_name = self._config.get("provider", "zai")
        active = self._config["providers"].get(active_name, {})
        for key in ZAI_PROFILE:
            if key in active:
                self._config[key] = active[key]

    def get_config(self) -> Dict[str, Any]:
        with self._lock:
            return self._config.copy()

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            provider = new_config.get("provider") or self._config.get("provider", "zai")
            if provider not in self._config["providers"]:
                provider = "zai"
            profile = self._config["providers"][provider]
            if "api_base_url" in new_config and new_config["api_base_url"]:
                profile["api_base_url"] = new_config["api_base_url"].strip().rstrip("/")
            for key in ("model_name", "api_key", "temperature", "max_tokens", "timeout_seconds"):
                if key in new_config and new_config[key] is not None:
                    profile[key] = new_config[key]
            self._config["provider"] = provider
            if "enabled" in new_config and new_config["enabled"] is not None:
                self._config["enabled"] = new_config["enabled"]
            self._apply_active()
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
            print(f"[LLMManager] Provider {provider}: {self._config.get('model_name')} at {self._config.get('api_base_url')}")
            return self._config.copy()

    def chat_completion(self, payload: Dict[str, Any], timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """OpenAI chat call against the active provider, with a short retry on 429."""
        cfg = self.get_config()
        base_url = cfg.get("api_base_url", "").rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.get('api_key') or 'EMPTY'}",
        }
        payload = dict(payload)
        payload["model"] = cfg.get("model_name")
        wait_budget = int(timeout if timeout is not None else cfg.get("timeout_seconds", 60))
        endpoint = f"{base_url}/chat/completions"
        for attempt in range(3):
            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=wait_budget)
            except Exception as e:
                print(f"[LLMManager] Call failed: {e}")
                return None
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429 and attempt < 2:
                retry_after = resp.headers.get("Retry-After", "2")
                try:
                    delay = min(float(retry_after), 65.0)
                except ValueError:
                    delay = 2.0
                print(f"[LLMManager] Rate limited, retrying in {delay:.0f}s")
                time.sleep(delay)
                continue
            print(f"[LLMManager] LLM responded with status {resp.status_code}: {resp.text[:300]}")
            return None
        return None

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to the active LLM endpoint (z.ai or vLLM)."""
        cfg = self.get_config()
        base_url = cfg.get("api_base_url", "").rstrip("/")
        model_name = cfg.get("model_name", "glm-4.7-flash")
        api_key = cfg.get("api_key", "EMPTY")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # 1. Try chat test ping
        chat_endpoint = f"{base_url}/chat/completions"
        try:
            ping_payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }
            resp = requests.post(chat_endpoint, headers=headers, json=ping_payload, timeout=8)
            if resp.status_code == 200:
                return {
                    "connected": True,
                    "status": "online",
                    "status_code": 200,
                    "available_models": [model_name],
                    "active_model": model_name,
                    "message": f"Successfully connected to {model_name} at {base_url}!"
                }
            elif resp.status_code in [400, 401, 403]:
                return {
                    "connected": False,
                    "status": "auth_or_model_error",
                    "status_code": resp.status_code,
                    "available_models": [],
                    "message": f"Server responded with error: {resp.text[:200]}"
                }
        except Exception as e:
            pass

        # 2. Try models endpoint (standard vLLM / OpenAI)
        models_endpoint = f"{base_url}/models"
        try:
            resp = requests.get(models_endpoint, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                model_list = []
                if "data" in data and isinstance(data["data"], list):
                    model_list = [m.get("id") for m in data["data"] if "id" in m]
                return {
                    "connected": True,
                    "status": "online",
                    "status_code": 200,
                    "available_models": model_list,
                    "active_model": model_name,
                    "message": f"Successfully connected! Found {len(model_list)} models on server."
                }
        except Exception as e:
            pass

        return {
            "connected": False,
            "status": "unreachable",
            "available_models": [],
            "message": f"Could not reach LLM endpoint at {base_url}."
        }

        api_key = cfg.get("api_key", "EMPTY")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

        # Standard OpenAI models endpoint
        models_endpoint = f"{base_url}/models"
        try:
            resp = requests.get(models_endpoint, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                model_list = []
                if "data" in data and isinstance(data["data"], list):
                    model_list = [m.get("id") for m in data["data"] if "id" in m]
                return {
                    "connected": True,
                    "status": "online",
                    "status_code": 200,
                    "available_models": model_list,
                    "active_model": cfg.get("model_name"),
                    "message": f"Successfully connected to vLLM! Found {len(model_list)} loaded model(s)."
                }
            else:
                return {
                    "connected": False,
                    "status": "error",
                    "status_code": resp.status_code,
                    "available_models": [],
                    "message": f"vLLM server returned HTTP {resp.status_code}: {resp.text[:200]}"
                }
        except requests.exceptions.ConnectionError:
            return {
                "connected": False,
                "status": "unreachable",
                "available_models": [],
                "message": f"Could not connect to vLLM at {base_url}. Ensure the notebook / vLLM server is running."
            }
        except Exception as e:
            return {
                "connected": False,
                "status": "error",
                "available_models": [],
                "message": f"Connection error: {str(e)}"
            }

    # How-to-play films must teach the whole game — short teasers are rejected.
    MIN_FILM_SECONDS = 180

    def generate_manim_code(
        self,
        game: Dict[str, Any],
        local_image_path: str,
        custom_instruction: Optional[str] = None,
        palette: Optional[Dict[str, str]] = None,
        research: Optional[str] = None,
        rules_digest: Optional[str] = None,
    ) -> Optional[str]:
        """
        Two passes, then one repair if needed.
        First the model writes a film treatment for this game alone.
        Then it shoots that treatment in Manim.
        Films under MIN_FILM_SECONDS of estimated runtime are rejected.
        """
        cfg = self.get_config()
        if not cfg.get("enabled", True):
            return None

        brief = self._game_brief(
            game, local_image_path, palette, research, custom_instruction, rules_digest
        )
        bgg_id = game["bgg_id"]
        model_name = cfg.get("model_name", "glm-4.7-flash")
        # A full 3+ minute film is slower than a chat reply.
        timeout = max(int(cfg.get("timeout_seconds", 60)), 300)

        print(f"[LLMManager] Directing a treatment for {game.get('name')} with {model_name}...")
        treatment = self._complete(
            "You are a director of tabletop how-to-play films. You never reuse another game's look. "
            "You write prose only, no code. Every film must teach the full game in at least three minutes.",
            self._treatment_prompt(brief),
            temperature=0.7,
            max_tokens=4000,
            timeout=timeout,
        )
        if not treatment or len(treatment.strip()) < 400:
            print("[LLMManager] Treatment was too thin. Asking for the film in one pass.")
            treatment = ""

        print(f"[LLMManager] Shooting Manim for {game.get('name')}...")
        code = self._shoot(brief, treatment, bgg_id, timeout)
        if code:
            return code

        print("[LLMManager] Shoot failed or film too short.")
        return None

    def estimate_runtime(self, code: str) -> float:
        """Approximate seconds from self.wait(...) and run_time= values in Manim code."""
        if not code:
            return 0.0
        waits = re.findall(r"(?:self\.)?wait\(\s*([0-9]*\.?[0-9]+)\s*\)", code)
        run_times = re.findall(r"run_time\s*=\s*([0-9]*\.?[0-9]+)", code)
        return sum(float(x) for x in waits) + sum(float(x) for x in run_times)

    def _game_brief(
        self, game, local_image_path, palette, research, custom_instruction, rules_digest=None
    ) -> str:
        weight = float(game.get("game_weight") or 2.5)
        pigments = ""
        if palette:
            pigments = (
                "Pigments sampled from the box (use them as paint from this world, not as a UI theme): "
                f"{palette.get('primary', '')}, {palette.get('secondary', '')}, "
                f"{palette.get('accent', '')}, ground near {palette.get('bg_dark', '#1a120b')}."
            )
        extra = f"\nAlso honor this note from the viewer: {custom_instruction}" if custom_instruction else ""
        research_block = (research or "").strip()[:1800]
        rules_block = (rules_digest or "").strip()[:4500]
        return f"""Title: {game.get('name')} ({game.get('year_published') or 'unknown year'})
BGG id: {game.get('bgg_id')}
Players: {game.get('min_players', 2)}-{game.get('max_players', 4)}
Playtime: {game.get('mfg_playtime', 45)} minutes
Weight: {weight:.1f} / 5
Categories: {game.get('categories') or 'unknown'}
Themes: {game.get('themes') or 'unknown'}
Mechanics: {game.get('mechanics') or 'unknown'}
{pigments}
Cover file: {local_image_path.replace(chr(92), '/')}

Publisher description:
{(game.get('description') or 'None on file.')[:2800]}

AUTHORITATIVE HOW-TO-PLAY RULES (teach every line — do not invent conflicting rules):
{rules_block or 'None curated. Use the publisher description and web notes carefully.'}

Notes gathered from the web (use only what clearly belongs to this game):
{research_block or 'None.'}
{extra}"""

    def _treatment_prompt(self, brief: str) -> str:
        return f"""Write a director's treatment for a COMPLETE how-to-play film of ONE board game.
This is a teaching film, not a teaser. Runtime target: 3 to 5 minutes (never under 3 minutes).

{brief}

Write these sections in prose:

WORLD
The era, place, materials, light, and motion specific to this title. Say what it must never look like.

WHAT A NEW PLAYER MUST LEAVE KNOWING
Cover EVERY part of the game using the authoritative rules above. Be concrete with real component names, costs, limits, and scoring numbers:
1) Goal / how you win
2) Every component and exact setup
3) Full turn structure — every phase named and explained
4) Core mechanic with one worked example (numbers, payments, placements)
5) Every scoring category and the win trigger
6) Opening / midgame / endgame strategy tips
If a rule is not in the material, say it is unknown. Do not invent a second game. Do not skip a section.

THE SHOTS
Plan enough shots for 180+ seconds of screen time. For every shot: what is on the table, what moves, what the viewer learns, and how long it holds (instructional holds 2–4 seconds after motion). Pieces should perform the rule. Include one full example turn. No two shots should share the same layout.

CRAFT
Where the eye should rest. What stays sparse. What should feel expensive.

Aim for 900–1600 words. No Python."""

    def _shoot(self, brief: str, treatment: str, bgg_id, timeout: int) -> Optional[str]:
        treatment_block = (
            treatment.strip()
            or "No separate treatment. Build a complete 3+ minute how-to-play film from the game brief and authoritative rules, covering every section."
        )
        min_sec = self.MIN_FILM_SECONDS
        prompt = f"""Shoot the treatment below as one Manim Community scene.
This must be a COMPLETE how-to-play film, not a trailer. Estimated wait()+run_time must total at least {min_sec} seconds.

GAME
{brief}

TREATMENT
{treatment_block}

MANDATORY CHAPTERS (each as its own clear sequence with a chapter title on screen)
1. Intro + goal / how you win
2. Components & setup — show and name every component from the rules
3. Turn sequence — every phase, one at a time, with a beacon or highlight moving across phases
4. Core mechanic demo — animate a concrete example with real costs/placements from the rules
5. Scoring & victory — every scoring line + win trigger
6. Strategy tips — opening, midgame, endgame
7. Brief outro

LENGTH & PACING
Sum of all self.wait(...) plus all run_time= values MUST be >= {min_sec}.
After instructional motion finishes, hold with self.wait between 2.0 and 4.0 seconds so the viewer can read.
Use run_time around 1.0–2.2 for plays. Prefer more shots over rushing.
If you are under budget, lengthen holds and add the missing chapter — never ship a short film.

HOW TO MAKE IT LOOK EXPENSIVE — ZERO VISUAL FLAWS
The frame is 14.2 by 8 units, 16:9. Hard safe area: every mobject must stay inside x -6.0 to 6.0 and y -3.2 to 3.2. No text, stroke, glow, spark, arrow tip, or piece may touch or cross the frame edge.
One idea occupies the frame at a time. Fade out what the next shot does not need so text never piles up or overlaps another card.
Build components as shapes the viewer can recognize: a board region, a card, a meeple-like token, a die, a track. Color, scale, and a soft surrounding stroke separate foreground from ground.
HYPER-POLISH BOX RULE (non-negotiable): every label lives INSIDE its RoundedRectangle / card / banner. Measure inner width = box.width - 0.5 and inner height = box.height - 0.36. Wrap on word boundaries. Shrink font from ~22 down to 11 until the Text fits. Prefer a slightly taller card over any overflow. Never let a letter, descender, or stroke stick past the rounded edge. Never place a badge, star, or icon past the parent box. Padding on all four sides is required.
Every word of a rule, phase, or tip must appear — do not ellipsize. If content is long, use more lines at a smaller size inside a taller card, still fully inside.
Titles 24-32, body 14-18, never below 11. Consistent left accent bars and even gaps between cards (0.2–0.3). Align card tops in a row.
The opening shot shows the cover with ImageMobject. The box floats gently; decorative pieces ON the cover (card, die, tokens) must stay inside the cover rectangle at all times — no sparks or sheens orbiting outside it.
Keep pieces moving in later shots: Write titles, slide tokens onto spaces, roll dice, grow arrows, Indicate / Circumscribe. Motion amplitudes stay small so pieces never leave their parent shapes.
The film is 1920x1080. At the top of the file, before the class, set:
from manim import config
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 30
Use rate_func=smooth. Camera pushes are allowed on MovingCameraScene when a detail deserves them; return to a readable wide shot afterward.
The background color is part of the world in the treatment. Set self.camera.background_color once to a hex that belongs there.

RULES OF THE RENDER
from manim import *
class GameExplainer_{bgg_id}(MovingCameraScene):
    def construct(self):
No MathTex, no Tex, no LaTeX. Only Text for words.
ImageMobject only for the cover file in the brief. Draw everything else.
Use mobjects and animations that ship with Manim Community: Text, VGroup, ImageMobject, Rectangle, RoundedRectangle, Square, Circle, Ellipse, Annulus, Arc, Line, Arrow, DashedLine, Polygon, RegularPolygon, Triangle, Dot, Star, Sector, SurroundingRectangle, and FadeIn, FadeOut, Create, Write, GrowFromCenter, Transform, ReplacementTransform, MoveToTarget, Circumscribe, Indicate, Flash, AnimationGroup, LaggedStart, Succession.
Never pass line_length= to Text, MarkupText, or Paragraph — that crashes Manim. Wrap with real newline characters in the string, or set width=. Flash alone may use line_length=.
Do not pass lagged_start= into self.play; use LaggedStart(...) instead.
Define every color you use as a hex string. Do not reference names you have not assigned. No markdown inside the code.
The file must parse.

Output only one python block."""
        raw = self._complete(
            "You are a Manim cinematographer shooting complete how-to-play films. "
            f"Runtime must be at least {min_sec} seconds. Output only executable Python.",
            prompt,
            temperature=0.45,
            max_tokens=12000,
            timeout=timeout,
        )
        code = self._scrub_invalid_manim_kwargs(self._extract_code(raw or ""))
        if self._code_is_usable(code, bgg_id):
            runtime = self.estimate_runtime(code)
            if runtime < min_sec:
                print(
                    f"[LLMManager] Shoot parsed but too short ({runtime:.0f}s < {min_sec}s). Rejecting."
                )
                return None
            print(f"[LLMManager] Shoot parsed (~{runtime:.0f}s estimated).")
            return code
        if not code:
            return None
        print("[LLMManager] Shoot did not parse. Sending it back for a repair.")
        err = self._syntax_error(code)
        repaired = self._complete(
            "You repair Manim Python. Keep the full teaching film. Fix only what stops it running.",
            f"""This script must define class GameExplainer_{bgg_id}(MovingCameraScene) with construct.
Syntax or structure problem: {err}
Never pass line_length= to Text/MarkupText/Paragraph. Use newlines or width= instead.
Preserve all chapters and duration (wait+run_time >= {min_sec}). Return the full corrected script in one python block. No MathTex or Tex.

{code[:16000]}""",
            temperature=0.2,
            max_tokens=12000,
            timeout=timeout,
        )
        fixed = self._scrub_invalid_manim_kwargs(self._extract_code(repaired or ""))
        if self._code_is_usable(fixed, bgg_id):
            runtime = self.estimate_runtime(fixed)
            if runtime < min_sec:
                print(
                    f"[LLMManager] Repair parsed but too short ({runtime:.0f}s < {min_sec}s). Rejecting."
                )
                return None
            print(f"[LLMManager] Repair parsed (~{runtime:.0f}s estimated).")
            return fixed
        print(f"[LLMManager] Repair still unusable: {self._syntax_error(fixed)}")
        return None

    def _scrub_invalid_manim_kwargs(self, code: str) -> str:
        """Strip kwargs that crash Manim Text/Paragraph (models often invent line_length=)."""
        if not code:
            return code
        banned = {"line_length", "lagged_start"}
        text_ctors = {"Text", "MarkupText", "Paragraph"}
        try:
            tree = ast.parse(code)

            class _Scrub(ast.NodeTransformer):
                def visit_Call(self, node: ast.Call):
                    self.generic_visit(node)
                    name = None
                    if isinstance(node.func, ast.Name):
                        name = node.func.id
                    if name in text_ctors:
                        node.keywords = [k for k in node.keywords if k.arg not in banned]
                    # self.play(..., lagged_start=True) is invalid — drop it
                    if (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "play"
                    ):
                        node.keywords = [k for k in node.keywords if k.arg != "lagged_start"]
                    return node

            tree = _Scrub().visit(tree)
            ast.fix_missing_locations(tree)
            return ast.unparse(tree)
        except SyntaxError:
            # Fallback regex when the draft does not parse yet
            scrubbed = re.sub(
                r"\b(Text|MarkupText|Paragraph)\s*\(((?:[^()]|\([^()]*\))*)\)",
                lambda m: f"{m.group(1)}("
                + re.sub(r",?\s*line_length\s*=\s*[^,\)]+", "", m.group(2))
                + ")",
                code,
            )
            scrubbed = re.sub(r",?\s*lagged_start\s*=\s*(True|False)", "", scrubbed)
            return scrubbed

    def _complete(self, system: str, user: str, temperature: float, max_tokens: int, timeout: int) -> Optional[str]:
        res = self.chat_completion(
            {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )
        if not res:
            return None
        msg = res["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning") or msg.get("reasoning_content") or ""

    def _code_is_usable(self, code: str, bgg_id) -> bool:
        if not code or f"class GameExplainer_{bgg_id}" not in code:
            return False
        if "def construct" not in code:
            return False
        if re.search(r"\b(MathTex|Tex)\b", code):
            return False
        return self._validate_python_syntax(code)

    def _syntax_error(self, code: str) -> str:
        if not code:
            return "empty response"
        try:
            ast.parse(code)
        except SyntaxError as e:
            return f"{e.msg} at line {e.lineno}"
        if "def construct" not in code:
            return "missing construct method or wrong class name"
        return "unknown"

    def _extract_code(self, raw_text: str) -> str:
        matches = re.findall(r"```(?:python)?\s*(.*?)```", raw_text, re.DOTALL)
        if matches:
            return matches[0].strip()
        return raw_text.strip()

    def _validate_python_syntax(self, code_str: str) -> bool:
        try:
            ast.parse(code_str)
            return True
        except SyntaxError as e:
            print(f"[LLMManager] Syntax error in generated code: {e}")
            return False

# Singleton instance
llm_manager = LLMManager()
