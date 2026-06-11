# AGENTS.md — Chasqui CLI

The **stack generator**: `uvx chasqui new <name>` scaffolds a configured
Chasqui project; `chasqui generate module <name>` scaffolds a Tool Module.
Part of [`chasqui-stack`](https://github.com/chasqui-stack/chasqui) — design
locked in the parent's `docs/design/adr-005-cli-generator.md`. **Read it
before changing behavior.**

## Stack & structure

Python ≥3.11 · `typer` (commands) · `questionary` (wizard) · `httpx`
(fetch) · `uv` · pytest. PyPI package: `chasqui`.

- `stack.py` — the pinned stack tag + repo map. **Bumped with every CLI
  release** (CLI vX.Y.Z scaffolds services vX.Y.Z).
- `wizard.py` — prompts + the `Answers` dataclass (defaults ARE the
  `--defaults` run).
- `envfiles.py` — pure renderers: answers → `.env` text (golden-testable).
- `fetch.py` — codeload tarballs, degit-style; `--source` copies a local
  checkout (dev escape hatch — codeload needs public repos).
- `rename.py` — explicit branding manifest. Never a blind sed.
- `provision.py` — best-effort steps; a failure prints its manual command
  and disables only its dependents.
- `module_gen.py` — the Tool Module templates (parent ARCHITECTURE §8;
  reference implementation `core/app/modules/faq/`).

## Key rules

- **The wizard asks only what is a `.env` variable** in a service
  `.env.example` (ADR-005). New question ⇒ the service grows the variable
  first, in its own PR.
- `.env`s are written **before** the first migrate — `EMBEDDING_DIM` is
  provision-time (ADR-001). Don't reorder the scaffold.
- `INTERNAL_API_KEY` is generated once and written into BOTH core and
  gateway `.env`s — byte-identical.
- The CLI must never import service code (it runs in uvx's ephemeral venv).
- Generated projects are ONE plain repo — no submodules.
- English-only code and output (the wizard's `locale` question only
  configures the generated agent, not this CLI).

## Dev

```bash
uv sync && uv run pytest
uv run chasqui new demo --defaults --skip-provision --source ~/path/to/chasqui
```

## Planning

PRPs and the sprint plan live in the parent repo (`chasqui/PRPs`,
`chasqui/docs`).

## Don't

- Add a template engine — the service repos ARE the template.
- Ask wizard questions that aren't `.env` vars.
- Blind-replace "chasqui" across the tree (it appears in code identifiers).
