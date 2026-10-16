# 🎲 Aatam: The Board Game Wiki on Steroids

**Aatam** is an intelligent, high-performance board game encyclopedia, recommendation engine, and procedural animation studio that teaches you how to play games using **Python Manim**.

Built on a master dataset of **94,998 board games** and real gamer rating profiles, Aatam runs entirely locally and free of charge, with zero expensive video generation APIs.

---

## 🌟 Core Features

### 1. 📖 Wiki on Steroids
- **Blazing Fast Indexed Catalog**: Fast search (<1ms query latency) powered by an indexed SQLite database across 94,998 games.
- **Deep Game Dossiers**: High-res box art, complexity weight gauge (1.0 - 5.0), community-voted player count recommendations, playtimes, Bayesian Geek Ratings, mechanics pills, and thematic genres.
- **Similar Games Carousel**: Algorithmic similarity matching on mechanics, themes, and complexity.

### 2. 👤 User Accounts & Email Sign-Up ("My Shelf")
- **Sign Up with Email**: Real user registration with email validation, unique usernames, display names, and salted PBKDF2 password hashing.
- **Session Tokens & Persistent Auth**: Secure bearer token sessions stored in `localStorage` that persist between visits.
- **Track Played Games**: Log plays, rate games on a 1.0 to 10.0 scale, and add notes synced directly to your account in `AatamDB`.
- **Pre-Loaded Legends**: Explore ratings from prominent community curators (e.g. Tom Vasel, Warta, OldGoat) or switch to your personal account.
- **Interactive Taste Analytics**: Visual SVG charts showing your rating distribution, top mechanics affinity meters, and average complexity preference.

### 3. ⚡ Personalized "Steroids" Recommendation Engine
- **Hybrid Matching Matrix**:
  - Analyzes your highly-rated games to build a dynamic taste vector across mechanics and themes.
  - Applies Gaussian complexity matching against your preferred weight sweet spot.
  - Weights community consensus and Bayesian rating quality.
- **Transparent Explainability**: Clear reasoning on every card (e.g., *"Shares Hand Management & Variable Player Powers with your 10/10 favorite Terraforming Mars"*).

### 4. 🎬 Python Manim Animated How-to-Play Video Engine
- **Procedural Code Synthesis**: Instead of slow, hallucinating video generation models, Aatam dynamically synthesizes clean, accurate **Python Manim** code tailored to the mechanics of each game.
- **Visuals Directly from Each Game**: Automatically downloads and formats high-resolution official box art and artwork directly from BGG image paths.
- **Mechanics-Specific Animations**:
  - **Tile Placement / Hex Grids**: Animated interconnecting terrain tiles and meeples.
  - **Card Drafting / Hand Management**: Fanning card decks with resource costs and ability triggers.
  - **Worker Placement / Action Selection**: Action wheels with animated token commitments.
  - **Turn Flow Processors**: 3-step circular turn diagrams.
  - **Victory Trackers**: Starburst victory condition milestones.
- **Interactive Video Player**: Embedded HTML5 player with chapter navigation (`0:00 Intro`, `0:04 Objective`, `0:08 Mechanics`, `0:12 Turn Flow`, `0:16 Victory`).
- **Live Manim Studio**: Inspect, edit, and re-render Python Manim code on demand with live status tracking.

### 5. 🤖 Hot-Swappable vLLM Integration (AMD ROCm / Jupyter Notebook)
- **Zero-Downtime Model Switching**: Hot-swap models on the fly through the web UI or REST API without restarting the server.
- **AMD Jupyter Notebook & ROCm Compatible**: Point Aatam to your vLLM server hosted on an AMD GPU notebook (e.g. `http://localhost:8001/v1` or an exposed tunnel IP).
- **Automatic Model Detection**: Automatically queries `/v1/models` to discover loaded models on your vLLM server.
- **Fault-Tolerant Hybrid Pipeline**: If the vLLM server is starting up or unreachable, Aatam automatically falls back to its deterministic procedural Manim engine so rule videos are always available.

---


## 🚀 Quick Start

### 1. Requirements
- Linux / Ubuntu (FFmpeg, Cairo, and Pango installed)
- Python 3.10+ (Manim, FastAPI, Uvicorn, Pandas, Scikit-Learn, Pillow, Requests)

### 2. Start the Server
```bash
./run.sh
```
Or directly with the virtual environment:
```bash
.venv/bin/uvicorn backend.server:app --host 0.0.0.0 --port 8000
```

Open your browser to:
👉 **`http://localhost:8000`**

---

## 🏗️ Architecture

```
Aatam/
├── backend/
│   ├── build_database.py     # ETL pipeline: master CSV -> optimized SQLite
│   ├── recommender.py        # Hybrid recommendation & taste profile engine
│   ├── manim_generator.py    # Python Manim code synthesizer & CLI renderer
│   └── server.py             # FastAPI REST server & background task worker
├── static/
│   ├── index.html            # Single-page glassmorphic UI
│   ├── css/style.css         # Cyber-tactile dark-mode design system
│   ├── js/app.js             # Client state, search, chapter video player
│   └── videos/               # Pre-rendered and on-demand MP4 explainer videos
├── data/
│   └── aatam.db              # Indexed SQLite database (95k games + user profiles)
├── generated_manim/          # Python Manim explainer scripts generated per game
└── processed_data/           # BGG Master Dataset (94,998 games)
```
