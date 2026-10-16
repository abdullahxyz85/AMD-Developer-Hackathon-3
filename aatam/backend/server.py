import os
import sqlite3
import threading
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .recommender import get_user_profile, recommend_games_for_user, get_similar_games
from .manim_generator import render_game_video, get_game_data, generate_manim_code, download_and_prepare_image
from .llm_manager import llm_manager

app = FastAPI(title="Aatam - Board Game Wiki & Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(PROJECT_DIR, "static")
VIDEOS_DIR = os.path.join(STATIC_DIR, "videos")
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "generated_manim")

# Track generation jobs in-memory
video_generation_jobs: Dict[int, Dict[str, Any]] = {}
generation_lock = threading.Lock()

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class PlayRequest(BaseModel):
    bgg_id: int
    rating: float
    played: int = 1
    notes: Optional[str] = ""

class CustomCodeRenderRequest(BaseModel):
    code: str
    quality: str = "l"

class SignUpRequest(BaseModel):
    email: str
    username: str
    password: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    played_games: Optional[List[int]] = None

class LoginRequest(BaseModel):
    login_id: str
    password: str

class GameSubmissionRequest(BaseModel):
    name: str
    year_published: Optional[int] = None
    min_players: Optional[int] = 2
    max_players: Optional[int] = 4
    mfg_playtime: Optional[int] = 45
    game_weight: Optional[float] = 2.5
    categories: Optional[str] = "Strategy; Thematic"
    mechanics: Optional[str] = "Hand Management; Action Selection"
    description: Optional[str] = ""
    image_path: Optional[str] = ""
    how_i_won: Optional[str] = ""
    winning_tips: Optional[str] = ""


class LLMConfigRequest(BaseModel):
    enabled: Optional[bool] = True
    provider: Optional[str] = None
    api_base_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 3000
    timeout_seconds: Optional[int] = None


from .aatam_db import aatam_db

@app.get("/api/games")
def list_games(
    q: Optional[str] = Query(None, description="Search query for game title"),
    category: Optional[str] = Query(None),
    mechanic: Optional[str] = Query(None),
    min_weight: Optional[float] = Query(None),
    max_weight: Optional[float] = Query(None),
    players: Optional[int] = Query(None),
    sort_by: str = Query("bayes_avg_rating", enum=["bayes_avg_rating", "avg_rating", "num_ratings", "name", "year_published"]),
    order: str = Query("desc", enum=["asc", "desc"]),
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100)
):
    offset = (page - 1) * limit
    # Query high-speed custom database
    rows, total_count = aatam_db.query(
        q=q,
        category=category,
        mechanic=mechanic,
        min_weight=min_weight,
        max_weight=max_weight,
        players=players,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset
    )

    # Enrich with video status
    for r in rows:
        vid_path = os.path.join(VIDEOS_DIR, f"{r['bgg_id']}.mp4")
        r["has_video"] = os.path.exists(vid_path) and os.path.getsize(vid_path) > 1000
        r["video_url"] = f"/static/videos/{r['bgg_id']}.mp4" if r["has_video"] else None

    return {
        "games": rows,
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit,
        "engine": "AatamDB Custom Columnar/Inverted Engine"
    }

def _get_authenticated_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in or create an account.")
    token = authorization.split(" ")[1]
    user = aatam_db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please sign in again.")
    return user

@app.get("/api/games/check-duplicate")
def check_duplicate_game(name: str = Query(..., description="Game title to verify")):
    is_dup, existing = aatam_db.check_is_duplicate_game(name)
    return {
        "is_duplicate": is_dup,
        "existing_game": existing if is_dup else None,
        "message": f"Game '{name}' already exists in catalog." if is_dup else "Game title is unique and ready for submission."
    }

@app.post("/api/games/submit")
def submit_new_game(req: GameSubmissionRequest, authorization: Optional[str] = Header(None)):
    user = _get_authenticated_user(authorization)
    try:
        new_entry = aatam_db.submit_game(req.dict(), username=user["username"])
        return {
            "status": "success",
            "message": f"Game '{new_entry['name']}' submitted successfully!",
            "game": new_entry
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/games/{bgg_id}")
def get_game(bgg_id: int):
    game = get_game_data(bgg_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    vid_path = os.path.join(VIDEOS_DIR, f"{bgg_id}.mp4")
    game["has_video"] = os.path.exists(vid_path) and os.path.getsize(vid_path) > 1000
    game["video_url"] = f"/static/videos/{bgg_id}.mp4" if game["has_video"] else None
    
    # Similar games
    game["similar_games"] = get_similar_games(bgg_id, limit=6)
    for sg in game["similar_games"]:
        sg_vid = os.path.join(VIDEOS_DIR, f"{sg['bgg_id']}.mp4")
        sg["has_video"] = os.path.exists(sg_vid) and os.path.getsize(sg_vid) > 1000
        sg["video_url"] = f"/static/videos/{sg['bgg_id']}.mp4" if sg["has_video"] else None

    return game

@app.get("/api/users")
def list_users():
    return {"users": aatam_db.get_users()}


@app.post("/api/auth/signup")
def signup(req: SignUpRequest):
    try:
        res = aatam_db.create_account(
            email=req.email,
            username=req.username,
            password=req.password,
            display_name=req.display_name,
            bio=req.bio,
            played_games=req.played_games
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/login")
def login(req: LoginRequest):
    try:
        res = aatam_db.login(login_id=req.login_id, password=req.password)
        return res
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/api/auth/me")
def get_current_user(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    auth_token = token
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ")[1]
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication token required")
    user = aatam_db.get_user_by_token(auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    return {"user": user}

@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    auth_token = token
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ")[1]
    if auth_token:
        aatam_db.logout(auth_token)
    return {"status": "success", "message": "Logged out successfully"}

@app.get("/api/users/{username}")
def get_user(username: str):
    profile = get_user_profile(username)
    # Enrich plays with video status
    for p in profile["plays"]:
        vid_path = os.path.join(VIDEOS_DIR, f"{p['bgg_id']}.mp4")
        p["has_video"] = os.path.exists(vid_path) and os.path.getsize(vid_path) > 1000
        p["video_url"] = f"/static/videos/{p['bgg_id']}.mp4" if p["has_video"] else None
    return profile


@app.get("/api/submissions")
def list_community_submissions():
    return {"submissions": aatam_db.get_all_submissions()}

@app.post("/api/users/{username}/plays")
def log_user_play(username: str, play: PlayRequest, authorization: Optional[str] = Header(None)):
    user = _get_authenticated_user(authorization)
    if user.get("username", "").lower() != username.lower():
        raise HTTPException(status_code=403, detail="Forbidden: You can only record plays to your own shelf.")
    aatam_db.save_user_play(username, play.bgg_id, play.rating, play.played, play.notes)
    return {"status": "success", "message": "Play saved to AatamDB successfully"}

@app.delete("/api/users/{username}/plays/{bgg_id}")
def remove_user_play(username: str, bgg_id: int, authorization: Optional[str] = Header(None)):
    user = _get_authenticated_user(authorization)
    if user.get("username", "").lower() != username.lower():
        raise HTTPException(status_code=403, detail="Forbidden: You can only delete plays from your own shelf.")
    aatam_db.delete_user_play(username, bgg_id)
    return {"status": "success", "message": "Play removed from AatamDB"}

@app.get("/api/users/{username}/recommendations")
def get_recommendations(
    username: str,
    limit: int = Query(12, ge=1, le=50),
    category: Optional[str] = Query(None),
    max_weight: Optional[float] = Query(None)
):
    recommendations = recommend_games_for_user(username, limit=limit, category=category, max_weight=max_weight)
    for r in recommendations:
        vid_path = os.path.join(VIDEOS_DIR, f"{r['bgg_id']}.mp4")
        r["has_video"] = os.path.exists(vid_path) and os.path.getsize(vid_path) > 1000
        r["video_url"] = f"/static/videos/{r['bgg_id']}.mp4" if r["has_video"] else None
    return {"recommendations": recommendations}

def background_video_task(bgg_id: int, quality: str = "h", username: Optional[str] = None):
    with generation_lock:
        video_generation_jobs[bgg_id] = {"status": "rendering", "progress": 10, "error": None}
    try:
        user_played = []
        if username:
            shelf_data = aatam_db.get_user_shelf(username)
            user_played = shelf_data.get("plays", [])
        render_game_video(bgg_id, quality=quality, overwrite=True, user_played_games=user_played)
        with generation_lock:
            video_generation_jobs[bgg_id] = {
                "status": "ready",
                "progress": 100,
                "video_url": f"/static/videos/{bgg_id}.mp4",
                "error": None
            }
    except Exception as e:
        with generation_lock:
            video_generation_jobs[bgg_id] = {"status": "error", "progress": 0, "error": str(e)}

@app.post("/api/generate-video/{bgg_id}")
def generate_video_endpoint(bgg_id: int, background_tasks: BackgroundTasks, quality: str = "h", username: Optional[str] = Query(None)):
    game = get_game_data(bgg_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    with generation_lock:
        current_job = video_generation_jobs.get(bgg_id)
        if current_job and current_job.get("status") == "rendering":
            return {"status": "already_running", "message": "Video rendering in progress"}

        video_generation_jobs[bgg_id] = {"status": "queued", "progress": 0, "error": None}

    background_tasks.add_task(background_video_task, bgg_id, quality, username)
    return {"status": "started", "message": f"Started video generation for {game['name']}"}

@app.get("/api/video-status/{bgg_id}")
def get_video_status(bgg_id: int):
    target_mp4 = os.path.join(VIDEOS_DIR, f"{bgg_id}.mp4")
    has_file = os.path.exists(target_mp4) and os.path.getsize(target_mp4) > 1000

    with generation_lock:
        job = video_generation_jobs.get(bgg_id)

    if job:
        return job

    if has_file:
        return {"status": "ready", "progress": 100, "video_url": f"/static/videos/{bgg_id}.mp4", "error": None}

    return {"status": "not_started", "progress": 0, "error": None}

@app.get("/api/manim-code/{bgg_id}")
def get_manim_code(bgg_id: int):
    game = get_game_data(bgg_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    script_path = os.path.join(SCRIPTS_DIR, f"explainer_{bgg_id}.py")
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()
    else:
        local_img = download_and_prepare_image(bgg_id, game.get("image_path", ""))
        code = generate_manim_code(game, local_img)
    return {"bgg_id": bgg_id, "name": game["name"], "code": code}

@app.post("/api/custom-manim-render/{bgg_id}")
def render_custom_code(bgg_id: int, req: CustomCodeRenderRequest, background_tasks: BackgroundTasks):
    game = get_game_data(bgg_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Save custom code
    script_path = os.path.join(SCRIPTS_DIR, f"explainer_{bgg_id}.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(req.code)

    def execute_custom():
        with generation_lock:
            video_generation_jobs[bgg_id] = {"status": "rendering", "progress": 10, "error": None}
        try:
            render_game_video(bgg_id, quality=req.quality, overwrite=True)
            with generation_lock:
                video_generation_jobs[bgg_id] = {
                    "status": "ready",
                    "progress": 100,
                    "video_url": f"/static/videos/{bgg_id}.mp4",
                    "error": None
                }
        except Exception as e:
            with generation_lock:
                video_generation_jobs[bgg_id] = {"status": "error", "progress": 0, "error": str(e)}

    background_tasks.add_task(execute_custom)
    return {"status": "started", "message": "Rendering custom Manim code"}

@app.get("/api/llm/config")
def get_llm_config():
    """Return the active vLLM model configuration."""
    return llm_manager.get_config()

@app.post("/api/llm/config")
def update_llm_config(req: LLMConfigRequest):
    """Hot-swap the active vLLM model without restarting the server."""
    updates = req.dict(exclude_unset=True)
    updated = llm_manager.update_config(updates)
    return {"status": "success", "message": "Model hot-swapped successfully", "config": updated}

@app.post("/api/llm/test")
def test_llm_connection():
    """Ping the configured vLLM endpoint and fetch loaded models."""
    return llm_manager.test_connection()

@app.get("/api/llm/models")
def get_llm_models():
    """Retrieve available models from the vLLM server."""
    res = llm_manager.test_connection()
    return {"models": res.get("available_models", []), "active": res.get("active_model")}

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

