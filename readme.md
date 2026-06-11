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

## Study Configuration Notes

-   `OTREE_AUTH_LEVEL=STUDY` enables participant-based access control.
-   `OTREE_PRODUCTION=1` enables production mode.
-   Proper configuration of `DATABASE_URL` and `REDIS_URL` is required
    for data persistence.

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
