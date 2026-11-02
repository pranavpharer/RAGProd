# RAGProd

A Python/FastAPI service for LLM-based question answering with reliability-focused backend features including model routing, response caching, API-key checks, rate limiting, automated tests, structured logging, request metrics and Docker configuration.

## Why I built it

The project explores how an LLM feature can be exposed through a maintainable backend service rather than only as a notebook or one-off demo. The focus is on clear API boundaries, predictable request/response handling, testability, diagnostics and basic operational safeguards.

## Main features

- Python/FastAPI backend
- structured request and response models
- primary/fallback model routing
- response caching
- API-key checks for protected/production-style usage
- rate limiting
- JSON/structured logging
- request metrics
- automated tests for model handling, caching and input/output behavior
- Docker configuration

## Architecture

```text
Client
  |
  v
FastAPI endpoint
  |
  +--> request validation
  |
  +--> cache check
  |
  +--> primary model
  |      |
  |      +--> fallback model when needed
  |
  +--> response validation
  |
  +--> logging + request metrics
  |
  v
Response
```

## What this project demonstrates

This repository is intended to demonstrate practical backend and Applied AI engineering skills:

- designing an API around an LLM workflow
- separating model behavior from API behavior
- adding failure-handling and fallback logic
- testing important paths rather than relying only on manual prompts
- adding logs and metrics so failures can be diagnosed
- packaging an application with Docker

## Example API flow

A typical request passes through input validation, cache lookup, model selection and response handling. Repeated requests can use the cache, while model-routing logic provides a fallback path if the primary model is unavailable or fails.

> Add one real `curl` request and one example JSON response from the repository here. Keep the example small and remove any API keys or private data.

## Running locally

Add the exact commands that work from a clean clone. A good README should make these steps copy/pasteable:

```bash
# 1. clone
# 2. create/activate environment
# 3. install dependencies
# 4. copy .env.example to .env
# 5. start FastAPI
```

Do not commit a real `.env` file or secrets.

## Tests

Document the exact command used to run the automated test suite, for example:

```bash
pytest
```

Only keep the command above if it matches the repository.

## Docker

Document the exact build/run commands used by this project. Keep them verified against a fresh clone.

## Engineering trade-offs and next steps

Useful next steps for a production deployment could include:

- persistent/shared caching rather than process-local caching
- a production database where appropriate
- stronger authentication/authorization
- CI that runs tests automatically on pull requests
- deployment to a managed cloud environment
- dashboards/alerts built on top of the existing logs and metrics
- load testing and explicit latency/error-rate targets

These are presented as future improvements, not as features already implemented.

## Author

Pranav Harer  
GitHub: https://github.com/pranavpharer  
LinkedIn: https://linkedin.com/in/pranav-harer-305220172
