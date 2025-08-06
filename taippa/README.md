# TAIPPA Influencer Marketing SaaS

This repository contains a skeleton implementation of **TAIPPA**, a production‑ready influencer marketing SaaS platform.  The goal of this codebase is to illustrate how the system can be structured to meet the extensive functional and technical requirements defined by the product specification.

The implementation uses **FastAPI** as the HTTP framework and **SQLAlchemy** with **PostgreSQL** for persistent storage.  Authentication is handled via JSON Web Tokens (JWTs) and role‑based access control (RBAC) is used to restrict access to routes based on user roles.  The project is organised into modular routers (users, brands, campaigns, influencers and AI analysis) to encourage separation of concerns and to simplify future expansion.

## Getting started

1.  Install dependencies using Poetry or pip:

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  Copy `.env.example` to `.env` and adjust values as needed.  The default configuration uses a local SQLite database for convenience, but PostgreSQL is recommended for production use.

3.  Start the development server:

    ```bash
    uvicorn taippa.main:app --reload
    ```

4.  Browse the interactive API documentation at `http://localhost:8000/docs`.

This skeleton is intentionally minimal.  Many subsystems (email automation, analytics dashboards, background processing) are stubbed out or omitted entirely.  The code is intended to demonstrate architectural patterns, not to provide a complete production system.
