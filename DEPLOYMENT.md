# Deployment Guide

This project deploys as four public services:

| Service        | IBM command                          | Port | Used by          |
| -------------- | ------------------------------------ | ---: | ---------------- |
| recommendation | `uvicorn recommendation.api:app`     | 8080 | tutor + frontend |
| rag            | `uvicorn app.main:app --app-dir RAG` | 8080 | tutor + frontend |
| tutor          | `uvicorn server.main:app`            | 8080 | frontend         |
| frontend       | Vercel                               |  443 | users            |

The AMD key stays only in the IBM tutor service. Never put it in Vercel
variables or commit `.env`.

## 1. Create an image registry

Use IBM Container Registry (the commands below use the `us.icr.io` namespace).
Build three focused images; recommendation does not need RAG or Manim, RAG does
not need Manim, and tutor does not need to rebuild the RAG index.

```powershell
ibmcloud login
ibmcloud plugin install container-registry
ibmcloud cr login
ibmcloud cr namespace-add YOUR_NAMESPACE
docker build -f Dockerfile.recommendation -t us.icr.io/YOUR_NAMESPACE/boardgame-recommend:latest .
docker build -f Dockerfile.rag -t us.icr.io/YOUR_NAMESPACE/boardgame-rag:latest .
docker build -f Dockerfile -t us.icr.io/YOUR_NAMESPACE/boardgame-tutor:latest .
docker push us.icr.io/YOUR_NAMESPACE/boardgame-recommend:latest
docker push us.icr.io/YOUR_NAMESPACE/boardgame-rag:latest
docker push us.icr.io/YOUR_NAMESPACE/boardgame-tutor:latest
```

Run each line separately in PowerShell. Do not paste the AMD key into any of
these commands.

The image build downloads the embedding model and creates the RAG index. The
first build is intentionally slow. Later builds reuse Docker layers.

## 2. Create an IBM Code Engine project

Code Engine has a free allowance in some account plans, but it is not safe to
assume every account or workload is free. Check the IBM billing page before
leaving public applications running. RAG and Manim need more memory than a
minimal web container.

```powershell
ibmcloud plugin install code-engine
ibmcloud ce project create --name boardgame-tutor
ibmcloud ce project select --name boardgame-tutor
```

## 3. Deploy recommendation and RAG first

Replace `YOUR_NAMESPACE` with the registry namespace from step 1.

```powershell
ibmcloud ce app create --name boardgame-recommend --image us.icr.io/YOUR_NAMESPACE/boardgame-recommend:latest --port 8080 --min-scale 1 --max-scale 1 --cpu 1 --memory 1G
ibmcloud ce app create --name boardgame-rag --image us.icr.io/YOUR_NAMESPACE/boardgame-rag:latest --port 8080 --min-scale 1 --max-scale 1 --cpu 2 --memory 4G
```

Get the generated HTTPS URLs:

```powershell
ibmcloud ce app get --name boardgame-recommend
ibmcloud ce app get --name boardgame-rag
```

Use the `URL` values in the next step. Test each before continuing:

```text
https://<recommend-url>/games
https://<rag-url>/health
```

## 4. Deploy the tutor backend

Set the AMD values in Code Engine secrets/environment variables. Do not paste
the AMD key into a Dockerfile, Git repository, shell history, or frontend
configuration.

```powershell
ibmcloud ce app create --name boardgame-tutor --image us.icr.io/YOUR_NAMESPACE/boardgame-tutor:latest --port 8080 --min-scale 1 --max-scale 1 --cpu 2 --memory 4G --env AMD_BASE_URL=https://developer.amd.com.cn/radeon/api/v1 --env AMD_MODEL=Gemma-4-31B-IT --env RECOMMEND_URL=https://<recommend-url> --env RAG_URL=https://<rag-url>
```

Immediately open the tutor app in the IBM console and add a secret-backed
environment variable named `RADEON_API_KEY`. Create the secret in the console,
enter the key there, and map it to that environment variable. The console is
deliberately used here because Code Engine CLI secret flags vary by plugin
version and the key must not enter PowerShell history.

Then test:

```text
https://<tutor-url>/health
```

## 5. Deploy the frontend on Vercel

In Vercel:

1. Import the repository.
2. Set **Root Directory** to `frontend`.
3. Build command: `npm run build`.
4. Output directory: `dist`.
5. Add these production environment variables:

```text
VITE_API_URL=https://<tutor-url>
VITE_RECOMMEND_URL=https://<recommend-url>
VITE_RAG_URL=https://<rag-url>
VITE_DEMO_FALLBACK=false
VITE_TIMEOUT_MS=600000
```

Redeploy after adding the variables because Vite embeds `VITE_*` values at
build time.

## 6. Production acceptance test

Open the Vercel URL and verify:

1. Choose `Monopoly` and `Chess` as known games.
2. Choose `Catan` as the target.
3. Generate a lesson and confirm sections, comparisons, sources, and quiz.
4. Submit a follow-up question.
5. Open the visual tab and confirm the SVG or Manim result loads.
6. In browser developer tools, confirm requests go to the three IBM HTTPS URLs
   and no request contains `RADEON_API_KEY`.

Do not use `localhost` URLs in Vercel variables. Do not deploy until the three
IBM `/health` or `/games` checks and one real `POST /lesson` succeed.
