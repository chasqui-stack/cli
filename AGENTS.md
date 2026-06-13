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
- **Provider packages follow the provider choice** (`wizard.PROVIDER_PACKAGES`):
  the core only bundles `langchain-google-genai`, so any other LLM/embeddings
  provider gets its `langchain-<provider>` installed via `uv add` at provision
  time (or printed as a manual step). A new provider in `LLM_PROVIDERS` /
  `EMBEDDING_PROVIDERS` MUST gain a `PROVIDER_PACKAGES` entry (test-guarded).
- The CLI must never import service code (it runs in uvx's ephemeral venv).
- Generated projects are ONE plain repo — no submodules.
- English-only code and output (the wizard's `locale` question only
  configures the generated agent, not this CLI).

## Dev

```bash
uv sync && uv run pytest
uv run chasqui new demo --defaults --skip-provision --source ~/path/to/chasqui
```

## Releasing a new version (the ceremony — order matters)

The CLI is release-critical: `uvx chasqui new` scaffolds the stack at the
tag pinned in `stack.py`, so services tag FIRST, then the CLI pins and
publishes. PyPI publishing is **trusted publishing** (no tokens): the
`publish.yml` workflow is registered as a trusted publisher on PyPI
(project `chasqui`, owner `chasqui-stack`, repo `cli`, environment `pypi`)
under Willy's account — pushing a `v*` tag IS the publish action.

1. **Tag the services** — in core, whatsapp and admin:
   `git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z`.
   In the parent: bump submodule pointers, commit, tag `vX.Y.Z`, push.
2. **Pin + bump the CLI** — `STACK_TAG = "vX.Y.Z"` in
   `src/chasqui/stack.py`, and the version in **BOTH**
   `pyproject.toml` and `src/chasqui/__init__.py` (two places, keep them
   equal). `uv run pytest`, commit, push.
3. **Publish** — `git tag -a vX.Y.Z && git push origin vX.Y.Z`. The tag
   triggers `publish.yml`: tests → `uv build` → PyPI. Watch it
   (`gh run watch`); if it fails BEFORE upload, fix, delete and re-push
   the tag. A version that reached PyPI is burned — never reusable, ship
   X.Y.Z+1.
4. **GitHub Releases** — `gh release create vX.Y.Z` here and on the
   parent (release notes live on the parent's).
5. **Verify from the wild** —
   `uvx chasqui@X.Y.Z --version` and
   `uvx chasqui new demo --defaults --skip-provision` in a scratch dir
   (this also proves the codeload fetch at the new tag).

Hard rules: never tag the CLI before the services' tags exist (step 5
would 404); a stack-only patch still needs a CLI release if `STACK_TAG`
must move.

## Planning

PRPs and the sprint plan live in the parent repo (`chasqui/PRPs`,
`chasqui/docs`).

## Don't

- Add a template engine — the service repos ARE the template.
- Ask wizard questions that aren't `.env` vars.
- Blind-replace "chasqui" across the tree (it appears in code identifiers).
