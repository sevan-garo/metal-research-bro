# 0018 — Defer Docker packaging until there's a real deployment target

## Context

Docker is the default reflex for "how do we ship this" in most projects, and
it was raised as a question worth deciding deliberately rather than by
default. This project's runtime shape argues against it at the POC stage:

- **Ollama needs the host's GPU.** On this machine (Apple Silicon), Ollama
  uses Metal for acceleration. Docker Desktop on macOS runs containers in a
  Linux VM that does not pass through the Apple GPU, so a containerized
  Ollama would fall back to CPU inference — a real, measurable slowdown on
  every single LLM call the agent makes (the router, and every answer
  generation), not a one-time cost.
- **Two dependencies live on the host, not in the app.** `search_zotero`
  talks to Zotero desktop's local API at `localhost:23119` (docs/adr/0009),
  and the LLM talks to Ollama at `localhost:11434`. Neither is a library the
  app bundles — both are separate running applications on the researcher's
  own machine. Containerizing the Python app alone would still need
  `host.docker.internal` networking to reach both, adding indirection
  without removing either host dependency.
- **There is nothing to reproduce yet.** Docker's value is consistency across
  environments — CI, a teammate's machine, a server. This is a single-user
  POC running on the one machine it was built for. There is no second
  environment it needs to match.

## Decision

Do not containerize the application at the POC stage. Keep running it
directly in the project's `.venv` against a natively-installed Ollama and
Zotero.

## Consequences

- No Docker-related files, no `host.docker.internal` networking, no
  Dockerfile to keep in sync with `requirements.txt` — one less thing to
  maintain for a single-user tool that has no other environment to
  reproduce.
- The GPU/networking trade-offs above are specific to this POC's shape
  (single user, local Ollama, local Zotero). They stop applying, and this
  decision should be revisited, once any of the following happens:
  - **Multi-user / production migration** (CLAUDE.md's Next Steps item 10):
    a server deployment has no "the researcher's own Mac" to lose GPU
    acceleration on, and consistency across environments becomes exactly
    the problem Docker solves.
  - **A hosted or remote LLM enters the picture** (e.g. swapping local Ollama
    for a hosted endpoint for some deployment tier): the GPU-passthrough
    argument disappears once inference isn't happening on the same machine
    as the container.
  - **Onboarding a second contributor or machine**: reproducing "install
    Homebrew, Python 3.11, Ollama, pull qwen2.5:7b, enable Zotero's local
    API" by hand doesn't scale past one person on one machine.
- Until one of those triggers, "should we add Docker" should be answered
  "not yet, see docs/adr/0018" rather than re-litigated from scratch.
