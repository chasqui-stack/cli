# chasqui — the stack generator

```bash
uvx chasqui new mi-agente
```

Zero to a configured, locally-running WhatsApp AI agent in one command — the
`rails new` of the [Chasqui stack](https://github.com/chasqui-stack/chasqui).

The wizard asks only what becomes a `.env` variable (LLM provider/model,
embeddings + dimension, where your Postgres is, WhatsApp credentials, default
language, first admin, optional media bucket / handoff notifications / deploy
params) — then downloads the three services at a pinned release tag
(degit-style, no git history), brands them, writes the `.env`s, generates the
shared secrets, and provisions: `uv sync` + `npm install` + `createdb` +
migrations + admin seed. Every step that can't run prints its manual command
and the scaffold continues.

Nothing is locked in: everything the wizard wrote lives in the generated
`.env`s and can be changed any time (the LLM applies on the next message).
The only provision-time choice is `EMBEDDING_DIM` — baked into the schema on
the first migrate.

## Commands

```bash
uvx chasqui new <name>                  # the wizard
uvx chasqui new <name> --defaults       # non-interactive (CI-friendly placeholders)
uvx chasqui new <name> --skip-provision # write files only
uvx chasqui new <name> --ref main       # scaffold an unreleased stack ref
uvx chasqui new <name> --source ~/path  # copy a local stack checkout (dev)

chasqui generate module <name>          # scaffold a Tool Module (run inside a project)
chasqui generate module <name> --with-models --with-admin
```

## Development

```bash
uv sync && uv run pytest
uv run chasqui new demo --defaults --skip-provision --source ~/path/to/chasqui
```

Design: [ADR-005](https://github.com/chasqui-stack/chasqui/blob/main/docs/design/adr-005-cli-generator.md).
Releases pin the stack tag (`src/chasqui/stack.py`): CLI `vX.Y.Z` scaffolds
services `vX.Y.Z`.

## License

Apache-2.0
