# Personalizing Human-LLM Interactions through Mixed Profiling

**oTree Open-Source Implementation**

This repository contains the open-source **oTree** implementation of the
*Mixed Profiling* approach introduced in:

Mueller, E., Greiner, K., Wegener, A., Kuhlmeier, F. O., & Maedche, A.
(2026).\
**Personalizing Human-LLM Interactions through Mixed Profiling.**\
Extended Abstracts of the 2026 CHI Conference on Human Factors in
Computing Systems (CHI EA '26), April 13--17, 2026, Barcelona, Spain.\
© 2026 The Authors. Licensed under CC BY 4.0.

------------------------------------------------------------------------

## Introduction

While Large Language Models (LLMs) are transitioning into companion
roles, current personalization approaches rely primarily on behavioral
data. Established psychometric methods (e.g., standardized
questionnaires assessing traits and states) are rarely integrated.

We introduce **Mixed Profiling**, a novel approach combining:

-   Standardized short questionnaires\
-   Adaptive LLM-based dialog\
-   Structured profile synthesis

In an online study (N=40) in the mental health context, participants
rated Mixed Profiling results as significantly more trustworthy than
basic questionnaire-only profiles. This work lays the foundation for
psychologically grounded and transparent personalization in human--LLM
interaction.

------------------------------------------------------------------------

## Technical Stack

-   oTree (experimental framework)
-   OpenAI API (LLM interaction)
-   PostgreSQL (database)
-   Redis (real-time communication)
-   Docker-compatible deployment

------------------------------------------------------------------------

## Required Environment Variables

### OpenAI Configuration

    OPENAI_KEY=your_openai_api_key
    OPENAI_MODEL=your_model_name
    OPENAI_URL=your_openai_endpoint

### Infrastructure

    DATABASE_URL=your_database_url
    REDIS_URL=your_redis_url

### oTree Configuration

    OTREE_ADMIN_PASSWORD=your_admin_password
    OTREE_SECRET_KEY=adsfeaertzpo2
    OTREE_AUTH_LEVEL=STUDY
    OTREE_PRODUCTION=1

------------------------------------------------------------------------

## Running the Project

### 1. Install dependencies

    pip install -r requirements.txt

### 2. Set environment variables

Copy the example file and fill in your values:

    cp .env.example .env

Variables in `.env` are loaded automatically when the app starts. Shell
environment variables take precedence if both are set.

Alternatively, export them in your shell (Linux/macOS):

    export OPENAI_KEY=...
    export DATABASE_URL=...

### 3. Run oTree

Development:

    otree devserver

Production:

    otree prodserver

Admin interface:

    /admin

------------------------------------------------------------------------

## Local stack with Docker (PostgreSQL + Redis)

oTree uses PostgreSQL whenever `DATABASE_URL` points at a postgres database
(otherwise it falls back to SQLite). `docker-compose.yml` provisions PostgreSQL
and Redis so the project runs on the same backend as production.

### Option A — backing services in Docker, oTree on the host (fast dev loop)

    cp .env.example .env          # then fill in OPENAI_* / OTREE_* secrets
    docker compose up -d db redis # start PostgreSQL + Redis
    otree resetdb                 # create the schema on PostgreSQL
    otree devserver               # http://localhost:8000

`.env` ships with `DATABASE_URL=postgresql://otree:otree@localhost:5432/otree`
and `REDIS_URL=redis://localhost:6379`, matching the compose services.

### Option B — full containerized stack (prodserver)

    docker compose run --rm web sh -c "yes | otree resetdb"  # one-time schema init
    docker compose up                                         # web + db + redis

The `web` service overrides `DATABASE_URL`/`REDIS_URL` to reach the `db` and
`redis` containers by hostname, so no `.env` changes are needed between options.

### Verifying the database

    docker compose exec db psql -U otree -d otree -c "\dt"   # tables exist after resetdb

Admin data export (CSV per app, including the Voice session's `custom_export`)
is available under `/admin` once the server is running.

------------------------------------------------------------------------

## Study Configuration Notes

-   `OTREE_AUTH_LEVEL=STUDY` enables participant-based access control.
-   `OTREE_PRODUCTION=1` enables production mode.
-   Proper configuration of `DATABASE_URL` and `REDIS_URL` is required
    for data persistence.

------------------------------------------------------------------------

## Data Analysis Pipeline

The `analysis/` package turns the study exports (oTree `all_apps_wide` CSV +
per-participant HRV recordings) into scored questionnaires, an automatically
segmented HRV analysis aligned to the session's own timestamps, engagement
metrics, per-participant HTML reports, and cohort-level (T1/T2/T3) comparison
tables — see `docs/analysis_pipeline.md`.

    python -m analysis --wide data/all_apps_wide.csv --hrv-dir data/hrv --out results

`data/` and `results/` are git-ignored: participant data never enters the repo.

------------------------------------------------------------------------

## Credits

This implementation builds upon and was inspired by:

https://github.com/clintmckenna/oTree_gpt

We thank the contributors of this repository for enabling structured LLM
integration in oTree experiments.

------------------------------------------------------------------------

## License

This project is released under the **Creative Commons Attribution (CC BY
4.0)** license.
