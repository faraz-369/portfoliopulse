# Deployment

Local: copy `.env.example` to `.env`, install Docker Desktop, then `docker compose up --build`. Compose starts PostgreSQL with a persistent volume, waits for database health, applies Alembic migrations, seeds demo accounts and launches FastAPI and Streamlit. Local URLs are in README. For non-Docker setup, install Python 3.12+, PostgreSQL and requirements, configure DATABASE_URL, run `alembic upgrade head`, seed, then launch Uvicorn and Streamlit separately. No cloud deployment is included or claimed.
