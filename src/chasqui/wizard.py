"""The `chasqui new` wizard.

Design rule (ADR-005): every prompt maps 1:1 to a `.env` variable that
already exists in a service `.env.example`. If a question would need new
service behavior, the variable lands in the service first.

Defaults are suggestions, not constraints: model fields are free text, and
everything the wizard writes lives in the generated `.env`s — swappable any
time after scaffolding (next message picks it up, no re-scaffold).
"""

from dataclasses import dataclass, field

import questionary

LLM_PROVIDERS = {
    # provider -> (default model, API key env var or None)
    "google": ("gemini-2.5-flash", "GOOGLE_API_KEY"),
    "anthropic": ("claude-sonnet-4-6", "ANTHROPIC_API_KEY"),
    "openai": ("gpt-5-mini", "OPENAI_API_KEY"),
    "openrouter": ("google/gemini-2.5-flash", "OPENROUTER_API_KEY"),
    # qwen3.5 resolves to Ollama's :latest (9b) — the floor for reliable
    # tool calling. qwen3.5:4b fits modest machines; 0.8b/2b don't agent.
    "ollama": ("qwen3.5", None),  # local — base URL instead of a key
}

EMBEDDING_PROVIDERS = {
    "google": ("gemini-embedding-001", "GOOGLE_API_KEY"),
    "openai": ("text-embedding-3-small", "OPENAI_API_KEY"),
    "ollama": ("nomic-embed-text", None),
}

FALLBACK_REPLIES = {
    "es": (
        "Lo siento, tuve un problema procesando tu mensaje. "
        "¿Puedes intentarlo de nuevo en un momento?"
    ),
    "en": (
        "Sorry, I had a problem processing your message. "
        "Could you try again in a moment?"
    ),
}


@dataclass
class Answers:
    """Everything `chasqui new` needs — defaults are the `--defaults` run."""

    project_name: str = "chasqui-agent"

    # LLM (core .env: LLM_PROVIDER / LLM_MODEL / <PROVIDER>_API_KEY)
    llm_provider: str = "google"
    llm_model: str = "gemini-2.5-flash"
    llm_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Embeddings (EMBEDDING_PROVIDER / EMBEDDING_MODEL / EMBEDDING_DIM —
    # provision-time: baked into the schema on first migrate, ADR-001)
    embedding_provider: str = "google"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    embedding_api_key: str = ""  # only when it differs from the LLM's

    # Postgres (POSTGRES_*) — "where is it", never "which engine" (ADR-002)
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_db: str = ""  # defaults to the project slug (underscored)

    # WhatsApp Business (gateway .env: WA_*) — skippable, fill later
    wa_configured: bool = False
    wa_phone_id: str = ""
    wa_token: str = ""
    wa_app_id: str = ""
    wa_app_secret: str = ""
    wa_waba_id: str = ""

    # One question, two files: VITE_DEFAULT_LOCALE (admin) + FALLBACK_REPLY
    # written in that language (core). English-only codebase untouched.
    locale: str = "es"
    fallback_reply: str = FALLBACK_REPLIES["es"]

    # First operator (seeded via core/scripts/create_admin.py)
    admin_email: str = "admin@example.com"
    admin_name: str = "Admin"
    admin_password: str = ""  # blank -> generated + printed

    # Extras (all optional)
    storage_endpoint_url: str = ""
    storage_bucket: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_region: str = ""
    notify_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    notify_email_to: str = ""

    # Deploy placeholders (Kamal deploy.yml) — optional
    deploy_domain: str = ""
    deploy_registry_user: str = ""
    deploy_server_ip: str = ""

    extra_api_keys: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        return self.project_name.lower().replace("_", "-").replace(" ", "-")

    @property
    def db_name(self) -> str:
        return self.pg_db or self.slug.replace("-", "_")

    @property
    def pg_is_local(self) -> bool:
        return self.pg_host in ("localhost", "127.0.0.1")


def _ask_llm(a: Answers) -> None:
    a.llm_provider = questionary.select(
        "LLM provider (swappable later in core/.env — never locked in):",
        choices=list(LLM_PROVIDERS),
        default=a.llm_provider,
    ).ask()
    default_model, key_var = LLM_PROVIDERS[a.llm_provider]
    a.llm_model = questionary.text(
        "LLM model (free text — any model the provider serves):",
        default=default_model,
    ).ask()
    if key_var:
        a.llm_api_key = questionary.password(f"{key_var}:").ask() or ""
    else:
        a.ollama_base_url = questionary.text(
            "Ollama base URL:", default=a.ollama_base_url
        ).ask()


def _ask_embeddings(a: Answers) -> None:
    a.embedding_provider = questionary.select(
        "Embeddings provider:",
        choices=list(EMBEDDING_PROVIDERS),
        default=(
            a.llm_provider if a.llm_provider in EMBEDDING_PROVIDERS else "google"
        ),
    ).ask()
    default_model, key_var = EMBEDDING_PROVIDERS[a.embedding_provider]
    a.embedding_model = questionary.text(
        "Embeddings model (free text):", default=default_model
    ).ask()
    a.embedding_dim = int(
        questionary.text(
            "Embedding dimension (PROVISION-TIME: baked into the schema on the "
            "first migrate; 768 recommended, <=2000 HNSW-indexable, 3072 uses "
            "halfvec):",
            default=str(a.embedding_dim),
        ).ask()
    )
    llm_key_var = LLM_PROVIDERS[a.llm_provider][1]
    if key_var and key_var != llm_key_var:
        a.embedding_api_key = (
            questionary.password(f"{key_var} (embeddings):").ask() or ""
        )


def _ask_postgres(a: Answers) -> None:
    where = questionary.select(
        "Where is your Postgres? (needs the pgvector extension)",
        choices=[
            "local (this machine)",
            "docker-compose (the generated one)",
            "managed / remote host",
        ],
    ).ask()
    if where.startswith("managed"):
        a.pg_host = questionary.text("Host:").ask()
        a.pg_port = int(questionary.text("Port:", default="5432").ask())
        a.pg_user = questionary.text("User:", default="postgres").ask()
        a.pg_password = questionary.password("Password:").ask() or ""
    elif where.startswith("docker"):
        a.pg_host, a.pg_user, a.pg_password = "localhost", "postgres", "postgres"
    else:
        a.pg_user = questionary.text("Postgres user:", default=a.pg_user).ask()
        a.pg_password = (
            questionary.password("Postgres password (blank if none):").ask() or ""
        )
    a.pg_db = questionary.text("Database name:", default=a.db_name).ask()


def _ask_whatsapp(a: Answers) -> None:
    a.wa_configured = questionary.confirm(
        "Configure WhatsApp Business credentials now? (you can fill "
        "whatsapp/.env later)",
        default=False,
    ).ask()
    if not a.wa_configured:
        return
    a.wa_phone_id = questionary.text(
        "WA_PHONE_ID (REQUIRED for operator replies from the inbox):"
    ).ask()
    a.wa_token = questionary.password("WA_TOKEN:").ask() or ""
    a.wa_app_id = questionary.text("WA_APP_ID:").ask()
    a.wa_app_secret = questionary.password("WA_APP_SECRET:").ask() or ""
    a.wa_waba_id = questionary.text("WA_WABA_ID:").ask()


def _ask_locale_and_admin(a: Answers) -> None:
    a.locale = questionary.select(
        "Default language (admin UI + fallback reply — the agent itself "
        "always replies in the user's language):",
        choices=list(FALLBACK_REPLIES),
        default=a.locale,
    ).ask()
    a.fallback_reply = questionary.text(
        "Fallback reply (sent verbatim when a turn fails):",
        default=FALLBACK_REPLIES[a.locale],
    ).ask()
    a.admin_email = questionary.text("First admin email:", default=a.admin_email).ask()
    a.admin_name = questionary.text("First admin name:", default=a.admin_name).ask()
    a.admin_password = (
        questionary.password("First admin password (blank = generate one):").ask()
        or ""
    )


def _ask_extras(a: Answers) -> None:
    extras = (
        questionary.checkbox(
            "Extras? (all optional, all .env-switchable later)",
            choices=[
                questionary.Choice("Media storage bucket (S3-compatible)", "storage"),
                questionary.Choice("Handoff webhook notification", "webhook"),
                questionary.Choice("Handoff email notification (SMTP relay)", "smtp"),
                questionary.Choice("Deploy placeholders (Kamal)", "deploy"),
            ],
        ).ask()
        or []
    )
    if "storage" in extras:
        a.storage_endpoint_url = (
            questionary.text("STORAGE_ENDPOINT_URL (blank for AWS S3):").ask() or ""
        )
        a.storage_bucket = questionary.text("STORAGE_BUCKET:").ask()
        a.storage_access_key = questionary.text("STORAGE_ACCESS_KEY:").ask()
        a.storage_secret_key = questionary.password("STORAGE_SECRET_KEY:").ask() or ""
        a.storage_region = questionary.text("STORAGE_REGION (blank if N/A):").ask() or ""
    if "webhook" in extras:
        a.notify_webhook_url = questionary.text("NOTIFY_WEBHOOK_URL:").ask()
    if "smtp" in extras:
        a.smtp_host = questionary.text("SMTP_HOST (e.g. smtp-relay.brevo.com):").ask()
        a.smtp_port = int(
            questionary.text("SMTP_PORT (587 STARTTLS / 465 SSL):", default="587").ask()
        )
        a.smtp_user = questionary.text("SMTP_USER:").ask()
        a.smtp_password = questionary.password("SMTP_PASSWORD:").ask() or ""
        a.smtp_from = questionary.text("SMTP_FROM:").ask()
        a.notify_email_to = questionary.text("NOTIFY_EMAIL_TO (comma-separated):").ask()
    if "deploy" in extras:
        a.deploy_domain = questionary.text(
            "Domain (api./wsp./admin. get prefixed):"
        ).ask()
        a.deploy_registry_user = questionary.text("Docker registry username:").ask()
        a.deploy_server_ip = questionary.text("Server IP:").ask()


def run_wizard(project_name: str) -> Answers:
    a = Answers(project_name=project_name)
    _ask_llm(a)
    _ask_embeddings(a)
    _ask_postgres(a)
    _ask_whatsapp(a)
    _ask_locale_and_admin(a)
    _ask_extras(a)
    return a


def default_answers(project_name: str) -> Answers:
    """`--defaults`: non-interactive, CI-friendly placeholders."""
    return Answers(project_name=project_name)
