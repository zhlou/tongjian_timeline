# Dockerfile Deployment Plan

## Goal

Containerize the **Zizhi Tongjian** web app for one-command deployment using a lightweight
Python image.

## Base image

**`python:3.12-slim`** (Debian-based, ~50 MB compressed)

Why:
- Minimal attack surface — no compilers, no dev headers, no git
- `slim` is smaller than `python:3.12` (~1 GB) but includes `pip`, so installing `flask`
  is a single line
- `alpine` was considered but adds friction (musl libc oddities, no pre-built wheels for
  some packages)

## Build plan (single-stage)

```
python:3.12-slim
  ├── apt-get update && apt-get install -y --no-install-recommends (if needed)    # typically nothing
  ├── COPY requirements.txt ./
  ├── RUN pip install --no-cache-dir -r requirements.txt                          # installs flask
  ├── COPY semantic_json/  ./semantic_json/        # 294 JSON source files
  ├── COPY scripts/         ./scripts/              # build_indices.py
  ├── COPY src/              ./src/                  # Flask app + templates + static
  ├── RUN python scripts/build_indices.py           # generate indices.json at build time
  ├── EXPOSE 5000
  └── CMD ["python", "src/app.py"]
```

## Files to include / exclude

| Include               | Reason                                  |
|-----------------------|-----------------------------------------|
| `requirements.txt`    | Install Flask                           |
| `semantic_json/`      | Input data for index builder            |
| `scripts/build_indices.py` | Generates `indices.json`     |
| `src/`                | Flask app, templates, static assets     |

| Exclude via `.dockerignore`   | Reason                         |
|-------------------------------|--------------------------------|
| `.venv/`, `__pycache__/`      | Not needed in container        |
| `raw_json/`, `raw_json_converted/` | Intermediate data; not used at runtime |
| `.git/`, `.gitignore`         | Build noise                    |
| `work/`, `README.md`, `AGENTS.md` | Docs only                  |
| `indices.json`                | Regenerated inside image       |

## Port

Expose **5000** (default Flask port, overridable via `PORT` env var).

## Runtime configuration

| Env var | Default   | Purpose           |
|---------|-----------|-------------------|
| `PORT`  | `5000`    | App listen port   |

## Build & run commands

```bash
# Build
docker build -t tongjian-timeline .

# Run
docker run -p 5000:5000 tongjian-timeline

# Run on custom port
docker run -p 8080:8080 -e PORT=8080 tongjian-timeline
```

## Future improvements (not in v1)

1. **Multi-stage build** — build `indices.json` in a builder stage, copy only the final
   artifact into the runtime stage (drops `semantic_json/` and `scripts/` from the
   runtime layer, saving ~4 MB)
2. **Non-root user** — create `appuser` and `chown` the app directory
3. **Waitress / gunicorn** — replace Flask dev server with a production WSGI server
4. **docker-compose.yaml** — add a compose file for convenience
5. **Healthcheck** — `HEALTHCHECK CMD curl -f http://localhost:5000/api/indices || exit 1`
