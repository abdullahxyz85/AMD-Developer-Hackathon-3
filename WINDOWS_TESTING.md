# Windows integration verification (17 October 2026)

Branch: tuan/windows-integration-fixes, based on origin/Full-Integration.

Fixes:
- Resolve npm.cmd on Windows and use its absolute path for install/dev subprocesses.
- Recognize .venv/Scripts/python.exe in addition to Unix venv paths.
- Set VITE_DEMO_FALLBACK=false in integrated launcher and require Vite port 5173.
- Correct backend default model ID to Gemma-4-31B-IT (matches .env.example and
  the model already tested by the team).

Verified on this Windows machine:
- 12 unittest checks pass (10 tutor + 2 launcher regression checks).
- Python subprocess launches resolved npm.cmd (npm 10.9.3).
- npm ci and npm run build succeed (TypeScript + Vite).
- Frontend HTTP / returns 200 on 127.0.0.1:5173.
- Actual backend /health returns 200 on 127.0.0.1:8002.
- TestClient CORS OPTIONS /lesson from localhost:5173 returns 200 with
  Access-Control-Allow-Origin: *.

Not verified: full browser lesson flow, live cloud generation through this
integration branch, Manim rendering, or multi-video navigation. No API key was
available in the test environment and Manim/ffmpeg are not installed. Prior
CLI cloud tests do not establish this branch's end-to-end behavior.

The screenshot's generic network/CORS error is not proof of a CORS defect.
Check backend health, configured System-page URLs, browser Network details and
backend logs. System-page endpoints saved in localStorage override build defaults;
reset them if they point to an old service. A remotely hosted frontend cannot
reach a developer's localhost services from another judge's machine.

## Run in PowerShell

Close old manually launched services first to avoid port collisions. Activate
your Python 3.13 environment. Keep the key in the root .env or shell environment,
never in frontend variables. Install the documented project dependencies before
using --skip-deps; video rendering additionally needs Manim and ffmpeg.

```powershell
cd "D:\SE193984\Hackathon\amd hackathon\AMD-Developer-Hackathon-3"
python main.py --skip-deps
```

Open http://127.0.0.1:5173. On the System page check tutor :8002,
recommendation :8001 and RAG :8100. Test Teach me Catan, sources, quiz,
follow-up questions and video rendering. Record actual failures before approval.
This document does not claim those flows have all passed.

## Live follow-up and renderer setup

User verified real lesson generation, quiz grading and follow-up answers from
the UI after restarting with the urllib-based AMD client. Transport root cause
was not proven; successful operation is observed, not a gateway diagnosis.

Installed on this machine: Manim 0.22.0, PyAV 19.0.1 and imageio-ffmpeg 0.6.0.
The latter includes a portable FFmpeg 7.1 executable; it does not add a global
ffmpeg command to PATH. Modern Manim/PyAV rendered the test without a PATH change.

```powershell
cd "D:\SE193984\Hackathon\amd hackathon\AMD-Developer-Hackathon-3"
python -m pip install "manim>=0.18" imageio-ffmpeg
```

Direct Catan render produced an MP4 with 109 decodable frames, 854x480 pixels,
7.27 seconds. Visual review found dark text on Manim's default black background;
scene setup now uses the existing PAPER palette for readable labels. Render
artifacts stay under ignored server/media/ and are not source assets to commit.
