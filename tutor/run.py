"""python -m tutor.run --help; standard-library HTTP, no Ollama SDK required."""
import argparse
import json
import os
from urllib.request import Request, urlopen
from .prompts import (Lesson, build_messages, prepare_context,
                      insufficient_lesson, validate_lesson)


def post(url, payload=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers=headers)
    with urlopen(request, timeout=600) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--known", nargs="+")
    parser.add_argument("--target")
    parser.add_argument("--goal", default="understand the first turn")
    parser.add_argument("--question")
    parser.add_argument("--recommend-url", default="http://127.0.0.1:8001/recommend")
    parser.add_argument("--rag-url", default="http://127.0.0.1:8100/rag/retrieve")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/api/chat")
    parser.add_argument("--provider", choices=["amd", "ollama"], default="amd")
    parser.add_argument("--base-url", default="https://developer.amd.com.cn/radeon/api/v1")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--model", help="Exact model ID from --list-models; required for generation")
    parser.add_argument("--dry-run", action="store_true", help="Call data APIs, print messages without calling LLM")
    args = parser.parse_args()
    key = os.environ.get("RADEON_API_KEY")
    if args.list_models:
        if not key:
            parser.error("Set RADEON_API_KEY in your environment first")
        models = post(args.base_url.rstrip("/") + "/models", key=key)
        print(json.dumps(models, indent=2, ensure_ascii=False))
        return
    if not args.known or not args.target:
        parser.error("--known and --target are required for lessons")
    if not args.dry_run:
        if not args.model:
            parser.error("Pass --model with an exact available model ID")
        if args.provider == "amd" and not key:
            parser.error("Set RADEON_API_KEY in your environment first")
    rec = post(args.recommend_url, {"known_games": args.known, "target_game": args.target})
    rag = post(args.rag_url, {"game": rec["target_game"], "query": args.question or args.goal,
                            "focus_mechanics": list(dict.fromkeys(m["mechanic"] for m in rec["per_mechanic"])), "k": 12})
    familiar_retrievals = []
    for game in dict.fromkeys(m["best_known_game"] for m in rec["per_mechanic"]):
        if game not in rec["player_known_games"]:
            continue
        mechanics = [m["mechanic"] for m in rec["per_mechanic"] if m["best_known_game"] == game]
        familiar_retrievals.append(post(args.rag_url, {
            "game": game, "query": "Explain " + ", ".join(mechanics) + ", objectives and key rules",
            "focus_mechanics": mechanics, "k": 6}))
    context = prepare_context(rec, rag, args.goal, args.question, familiar_retrievals)
    if args.dry_run:
        result = {"messages": build_messages(context), "evidence": context["evidence"]}
    else:
        if context["insufficient_evidence"]:
            lesson = insufficient_lesson(context)
        else:
            if args.provider == "amd":
                response = post(args.base_url.rstrip("/") + "/chat/completions", {
                    "model": args.model, "messages": build_messages(context),
                    "stream": False, "response_format": {"type": "json_object"},
                    "reasoning_effort": "low", "max_tokens": 4096,
                    "temperature": 0.2}, key=key)
                choice = response["choices"][0]
                if choice.get("finish_reason") == "length":
                    raise ValueError("Model token limit reached; retry with a larger max_tokens budget")
                content = choice["message"].get("content")
                if not content:
                    raise ValueError("Model returned empty content")
            else:
                response = post(args.ollama_url, {"model": args.model, "stream": False,
                    "messages": build_messages(context), "format": Lesson.model_json_schema(),
                    "options": {"temperature": 0.2}})
                content = response["message"]["content"]
            lesson = validate_lesson(content, context)
        result = {"lesson": lesson.model_dump(), "evidence": context["evidence"]}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
