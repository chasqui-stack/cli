"""`chasqui generate module <name>` — scaffolds the Tool Module anatomy.

The module contract (parent ARCHITECTURE §8, reference implementation
`core/app/modules/faq/`): a package exposing a module-level `module`
attribute, auto-discovered at startup. The admin form for the config knobs
comes free — `config_schema()` → JSON Schema → auto-rendered in `/tools`.
"""

import re
from pathlib import Path

SNAKE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class ModuleGenError(RuntimeError):
    pass


INIT_TEMPLATE = '''"""{title} module.

Describe what this module gives the agent. Tools are discovered from
`register_tools()`; enable/disable per tool lives in the admin panel.
"""

import logging

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.services.agent_context import TurnContext

logger = logging.getLogger(__name__)


class {camel}Config(BaseModel):
    """Knobs surfaced in the admin panel (agent_config.tool_config['{name}']).

    Keep it FLAT (str/int/float/bool only) so the admin auto-renders a form.
    """

    example_knob: int = Field(default=3, ge=1, le=10, description="Replace me")


def _tool_config(ctx: TurnContext) -> {camel}Config:
    raw = (ctx.config.tool_config or {{}}).get("{name}", {{}})
    try:
        return {camel}Config(**raw)
    except Exception:  # bad admin-entered config must not break the turn
        logger.warning("Invalid {name} tool_config %r; using defaults", raw)
        return {camel}Config()


@tool
async def {name}(query: str, runtime: ToolRuntime[TurnContext]) -> str:
    """One-line description the LLM reads to decide WHEN to call this.

    Explain what the tool does and when to use it. The docstring IS the
    tool's prompt — write it for the model, in English, and describe every
    argument:

    Args:
        query: What the user needs (e.g. "...").
    """
    ctx = runtime.context
    config = _tool_config(ctx)
    # ctx.session is an AsyncSession; ctx.contact / ctx.conversation are loaded.
    return f"TODO: implement {name} (example_knob={{config.example_knob}})"


class {camel}Module:
    """{title}: one-line summary for the admin panel."""

    name = "{name}"
    config_key = "{name}"  # where the knobs live in agent_config.tool_config

    def register_tools(self):
        return [{name}]
{models_method}{admin_method}
    def config_schema(self):
        return {camel}Config


module = {camel}Module()
'''

MODELS_METHOD = """
    def register_models(self):
        from app.modules.{name}.models import {camel}Record

        return [{camel}Record]
"""

ADMIN_METHOD = """
    def register_admin_routes(self, router):
        from app.modules.{name}.admin import register

        register(router)
"""

MODELS_TEMPLATE = '''"""{title} tables — registered via the module's `register_models()`.

After defining the model, generate the migration from core/:
    make makemigrations m="add {name} tables"
    make migrate
"""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class {camel}Record(SQLModel, table=True):
    __tablename__ = "{name}_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # TODO: your columns
'''

ADMIN_TEMPLATE = '''"""{title} admin endpoints — mounted under /admin/modules/{name} (JWT)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel


class {camel}Item(BaseModel):
    id: uuid.UUID
    created_at: datetime


class {camel}ListResponse(BaseModel):
    items: list[{camel}Item]
    total: int


def register(router: APIRouter) -> None:
    @router.get("/records", response_model={camel}ListResponse)
    async def list_records(
        limit: int = Query(default=50, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> {camel}ListResponse:
        # TODO: query your tables ({{items, total}} envelope, like faq/handoff)
        return {camel}ListResponse(items=[], total=0)
'''

TEST_TEMPLATE = '''"""Contract tests for the {name} module."""

from app.modules.{name} import module


def test_module_contract():
    assert module.name == "{name}"
    tools = module.register_tools()
    assert tools, "the module must expose at least one tool"
    assert all(t.description for t in tools), "tool docstrings are the LLM prompt"


def test_config_schema_is_flat():
    schema = module.config_schema().model_json_schema()
    for prop in schema.get("properties", {{}}).values():
        assert prop.get("type") in ("string", "integer", "number", "boolean"), (
            "keep config schemas FLAT so the admin auto-renders the form"
        )
'''


def _camel(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _find_core(start: Path) -> Path:
    """Accept running from the project root or from inside core/."""
    for candidate in (start / "core", start):
        if (candidate / "app" / "modules").is_dir():
            return candidate
    raise ModuleGenError(
        "No core/app/modules directory found — run this inside a Chasqui "
        "project (or its core/)"
    )


def generate(
    name: str,
    *,
    cwd: Path,
    with_models: bool = False,
    with_admin: bool = False,
) -> list[Path]:
    if not SNAKE_RE.match(name):
        raise ModuleGenError(
            f"'{name}' is not a valid module name — use snake_case "
            "(lowercase letters, digits, underscores)"
        )
    core = _find_core(cwd)
    module_dir = core / "app" / "modules" / name
    if module_dir.exists():
        raise ModuleGenError(f"{module_dir} already exists")

    title = name.replace("_", " ").capitalize()
    camel = _camel(name)
    ctx = {"name": name, "camel": camel, "title": title}

    created: list[Path] = []
    module_dir.mkdir(parents=True)

    init_src = INIT_TEMPLATE.format(
        **ctx,
        models_method=MODELS_METHOD.format(**ctx) if with_models else "",
        admin_method=ADMIN_METHOD.format(**ctx) if with_admin else "",
    )
    created.append(_write(module_dir / "__init__.py", init_src))

    if with_models:
        created.append(_write(module_dir / "models.py", MODELS_TEMPLATE.format(**ctx)))
    if with_admin:
        created.append(_write(module_dir / "admin.py", ADMIN_TEMPLATE.format(**ctx)))

    tests_dir = core / "tests" / "modules"
    tests_dir.mkdir(parents=True, exist_ok=True)
    created.append(_write(tests_dir / f"test_{name}.py", TEST_TEMPLATE.format(**ctx)))

    return created


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path
