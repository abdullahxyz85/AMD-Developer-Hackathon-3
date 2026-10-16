"""server — main tutor backend for the Personalized AI Board-Game Tutor.

Glues together:
  recommendation/  (port 8001)  POST /recommend
  RAG/             (port 8100)  POST /rag/retrieve
  tutor/           (library: prompts.py — context building + lesson validation)
  AMD Token Factory (LLM inference)
  Manim renderer   (this package) for POST /visual

Run from the repository root:
  python -m uvicorn server.main:app --port 8002
"""
