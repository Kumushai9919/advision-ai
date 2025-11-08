## Kiosk Biometric Auth

A containerized FastAPI service and worker ecosystem for face-based kiosk authentication. This repository contains a FastAPI backend, a face-recognition worker, message broker configuration, object storage scaffolding (MinIO), and convenience scripts and Docker Compose files to run the whole system locally.

## Key features
- FastAPI backend with authentication and user management APIs
- Worker process for face recognition tasks (RabbitMQ-based task queue)
- Local object storage using MinIO for face images
- PostgreSQL for persistent data and RabbitMQ for messaging
- Docker Compose development setup that wires all services together

## Repository layout (top-level)
- `backend/` — FastAPI application, Dockerfile, requirements, and server code (`src/`)
- `fr_worker/` — face recognition worker, Dockerfile, and worker code
- `broker/` — message producer/consumer examples and RabbitMQ configuration
- `object_storage/` — local MinIO data volume used by compose
- `docker-compose.yml` — brings up Postgres, RabbitMQ, MinIO, the FastAPI app, and the worker
- `test/` — unit and integration tests

## Getting started

### Prerequisites
- Docker & Docker Compose (v1.27+/compose v2 recommended)
- (Optional) Python 3.11+ for local backend development
- (Optional) VS Code for workspace tasks (there is a task to build/upload firmware)

### Quickstart (recommended) — run everything with Docker Compose

1. Copy or review backend environment variables:

```bash
cp backend/.env.example backend/.env  # if an example exists, or create backend/.env
# Edit backend/.env to set secrets and configuration (DB, RABBITMQ, MINIO credentials)
```

2. Start the stack:

```bash
docker compose up --build
```

- The API will be available at http://localhost:8000
- FastAPI interactive docs: http://localhost:8000/docs (OpenAPI / Swagger UI)
- MinIO console: http://localhost:9001
- RabbitMQ management UI: http://localhost:15672

Notes:
- The `docker-compose.yml` contains healthchecks and a one-off `minio-setup` service which creates the `face-images` bucket and applies a policy.
- Database data is persisted to the `postgres_data` volume defined in compose.

### Run backend locally (without Docker)

1. Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies and run the backend (from `backend/`):

```bash
cd backend
pip install -r requirements.txt
# run the app (development):
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

3. Confirm the API at http://localhost:8000/api/v1/health

### Run the face recognition worker locally

The worker connects to RabbitMQ and the backend API. When using Docker Compose the correct networking and env vars are already provided.

To run locally (developer mode):

```bash
cd fr_worker
pip install -r requirements.txt
# run the worker entrypoint (module name depends on the file layout in fr_worker)
python face_worker.py
```

Adjust environment variables to point to the RabbitMQ host, credentials and API URL.

## Development notes

- Backend code lives in `backend/src/`. The application lifecycle and routes are registered in `backend/src/main.py`.
- The backend creates tables on startup (SQLAlchemy `Base.metadata.create_all(bind=engine)` is invoked in the lifespan handler).
- API mount points are under `/api/v1/` (see `settings.API_V1_PREFIX` in `src/core/config.py`).

## Testing

- Unit and integration tests are in `test/` and `fr_worker/test*` files. Run tests with pytest from repository root:

```bash
pytest -q
```

## Configuration and environment variables

- Top-level `docker-compose.yml` references environment variables for Postgres, RabbitMQ, MinIO, and worker configuration. See that file for defaults and examples.
- Backend-specific configuration is read from `backend/.env` (the `app` service in compose uses `env_file: ./backend/.env`).

## Where to get help

- Read in-repo docs and `backend/README.md` for backend-specific instructions.
- Open an issue in this repository for bugs or feature requests.
- For questions about running the stack, include the `docker compose logs` output and environment values (avoid secrets) when filing issues.

## Maintainers & contributing

- Maintainer: Repository owner (see project settings on GitHub)
- Contribution guidelines: please open issues or PRs. If you plan to contribute code, add tests and follow the existing code style. For larger changes, open an issue to discuss the design first.
- See `CONTRIBUTING.md` (if present) for more details — a link is provided here as a relative reference: `CONTRIBUTING.md`.

## Security & license

- Do not commit secrets or credentials. Use `backend/.env` locally and CI secrets in your CI provider.
- Licensing information is in `LICENSE` (refer to that file for full terms).

## Quick reference — useful commands

```bash
# Start the development stack (build images if needed)
docker-compose up -d

# Stop and remove containers
docker-compose down

# Build and run backend locally
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload

# Run tests
pytest -q
```