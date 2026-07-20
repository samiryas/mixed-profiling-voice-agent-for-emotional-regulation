# Mixed Profiling Voice Agent for Emotional Regulation

**oTree implementation — Biosignal-Adaptive Systems Seminar (KIT)**

This repository contains the oTree codebase for a lab study evaluating whether
**Mixed Profiling–based personalization** improves a voice-based **emotion
regulation coaching session** (cognitive reappraisal), and whether **real-time
voice-based emotional state adaptation** adds further benefit on top of static
personalization.

It builds on the open-source oTree implementation of the *Mixed Profiling*
approach introduced in:

> Mueller, E., Greiner, K., Wegener, A., Kuhlmeier, F. O., & Maedche, A. (2026).
> **Personalizing Human-LLM Interactions through Mixed Profiling.**
> Extended Abstracts of the 2026 CHI Conference on Human Factors in Computing
> Systems (CHI EA '26), April 13–17, 2026, Barcelona, Spain.
> © 2026 The Authors. Licensed under CC BY 4.0.

---

## Background: Mixed Profiling

While Large Language Models (LLMs) are transitioning into companion roles,
current personalization approaches rely primarily on behavioral data.
Established psychometric methods (e.g., standardized questionnaires assessing
traits and states) are rarely integrated.

**Mixed Profiling** combines:

- Standardized short questionnaires (**BFI-10** for Big Five personality,
  **ERQ** for habitual emotion regulation)
- An adaptive LLM-based refinement dialogue that clarifies ambiguous or
  low-confidence dimensions one at a time
- Structured synthesis into a narrative user profile (dialogue information is
  preferred over questionnaire scores in cases of conflict)

In an online study (N=40) in the mental health context, participants rated
Mixed Profiling results as significantly more trustworthy than basic
questionnaire-only profiles.

---

## The study built on this codebase

**Design:** between-subjects, three conditions, exploratory proof-of-concept
(small N, effect sizes and descriptive patterns rather than significance
testing). Physical lab setting at KIT.

| Condition | Profile | Delivery | Real-time adaptation |
|---|---|---|---|
| **T1 — Non-personalized** | Profiling completed, but withheld from the agent | Neutral | None |
| **T2 — Personalized** | Mixed Profiling (BFI-10 + ERQ + dialogue) injected into the agent | ERQ-based framing + Big Five delivery adaptation | None |
| **T3 — Personalized + Adaptive** | Same as T2 | Same as T2 | Voice sentiment + acoustic features drive state-based prompt adaptation |

All three conditions teach the same technique — **cognitive reappraisal** —
in a four-phase voice session (check-in, technique introduction, guided
practice, reflection). Personalization changes delivery style and framing
only, never the technique itself. Heart rate variability (Polar H10, RMSSD)
is recorded as an evaluation metric; it does not feed into real-time
adaptation.

### Repository status

The **Mixed Profiling pipeline** (this repository's current contents) is the
implemented foundation: questionnaire administration, LLM profiling chat, and
profile synthesis as an oTree experiment. The **voice session module** (local
STT, LLM coaching agent, TTS, T3 sentiment/acoustic adaptation) and the
**HRV recording pipeline** are developed as part of the same project and are
integrated on top of this base.

---

## Repository structure

```
├── Introduction/     # Consent, onboarding, BFI-10 / ERQ questionnaires
├── Chat/             # LLM-based Mixed Profiling refinement dialogue (live pages)
├── Evaluation/       # Profile evaluation / rating pages
├── Outro/            # Debrief and completion (Prolific return supported)
├── utils/
│   ├── ai.py         # Async OpenAI-compatible client, structured output helpers
│   └── promting.py   # Prompt construction
├── _static/          # Static assets
├── _templates/       # Global templates
├── settings.py       # oTree session configs (FullExperiment + per-app demos)
├── load_env.py       # .env loading (shell variables take precedence)
├── Dockerfile        # Container deployment (Python 3.13)
└── Procfile          # Two-process production deployment (web + worker)
```

The `FullExperiment` session config runs the apps in sequence:
`Introduction → Chat → Evaluation → Outro`.

---

## Technical stack

- **oTree 6** — experimental framework; all modules share one codebase and one
  database
- **OpenAI-compatible API** — LLM interaction via a configurable endpoint
  (`OPENAI_URL`), supporting KIT-hosted local models so that personal data
  never leaves KIT infrastructure
- **PostgreSQL** — data persistence
- **Redis** — real-time communication
- **Docker-compatible deployment**

---

## Required environment variables

### LLM configuration

    OPENAI_KEY=your_api_key
    OPENAI_MODEL=your_model_name
    OPENAI_URL=your_openai_compatible_endpoint

### Infrastructure

    DATABASE_URL=your_database_url
    REDIS_URL=your_redis_url

### oTree configuration

    OTREE_ADMIN_PASSWORD=your_admin_password
    OTREE_SECRET_KEY=your_secret_key
    OTREE_AUTH_LEVEL=STUDY
    OTREE_PRODUCTION=1

---

## Running the project

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

### Docker

    docker build -t mixed-profiling .
    docker run --env-file .env -p 8000:8000 mixed-profiling

---

## Study configuration notes

- `OTREE_AUTH_LEVEL=STUDY` enables participant-based access control.
- `OTREE_PRODUCTION=1` enables production mode.
- Proper configuration of `DATABASE_URL` and `REDIS_URL` is required for data
  persistence.
- System prompts and adaptation logic are version-controlled in this
  repository for methods reporting and reproducibility.

---

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

- https://github.com/clintmckenna/oTree_gpt — structured LLM integration in
  oTree experiments, including the `chat_voice` template that the voice
  session module is based on.

We thank the contributors of this repository.

---

## License

This project is released under the **Creative Commons Attribution (CC BY 4.0)**
license.
