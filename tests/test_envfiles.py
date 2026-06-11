from chasqui import envfiles
from chasqui.secrets_gen import GeneratedSecrets
from chasqui.wizard import Answers, default_answers


def _render_all(a: Answers):
    s = GeneratedSecrets()
    return s, envfiles.render_core_env(a, s), envfiles.render_whatsapp_env(a, s)


def test_internal_api_key_identical_in_both_envs():
    s, core, wa = _render_all(default_answers("demo"))
    assert f"INTERNAL_API_KEY={s.internal_api_key}" in core
    assert f"INTERNAL_API_KEY={s.internal_api_key}" in wa


def test_core_env_defaults():
    a = default_answers("mi-agente")
    s, core, _ = _render_all(a)
    assert "APP_NAME=mi-agente" in core
    assert "POSTGRES_DB=mi_agente" in core
    assert "LLM_PROVIDER=google" in core
    assert "GOOGLE_API_KEY=fill-me" in core
    assert "EMBEDDING_DIM=768" in core
    assert f"JWT_SECRET_KEY={s.jwt_secret_key}" in core
    assert "CHANNEL_WHATSAPP_SEND_URL=http://localhost:8000/send" in core
    assert "FALLBACK_REPLY=Lo siento" in core  # default locale is es


def test_provider_key_vars_follow_the_choice():
    a = default_answers("demo")
    a.llm_provider, a.llm_model = "anthropic", "claude-sonnet-4-6"
    a.llm_api_key = "sk-ant-test"
    _, core, _ = _render_all(a)
    assert "ANTHROPIC_API_KEY=sk-ant-test" in core
    # embeddings stay google -> the google key is still requested
    assert "GOOGLE_API_KEY=fill-me" in core


def test_ollama_gets_base_url_not_key():
    a = default_answers("demo")
    a.llm_provider, a.llm_model = "ollama", "qwen3.5"
    a.embedding_provider, a.embedding_model = "ollama", "nomic-embed-text"
    _, core, _ = _render_all(a)
    assert "OLLAMA_BASE_URL=http://localhost:11434" in core
    assert "API_KEY" not in core.replace("INTERNAL_API_KEY", "")


def test_storage_and_smtp_blocks_render_when_configured():
    a = default_answers("demo")
    a.storage_bucket, a.storage_access_key, a.storage_secret_key = "b", "ak", "sk"
    a.smtp_host, a.smtp_user, a.smtp_from = "smtp-relay.brevo.com", "u", "f@x.com"
    a.notify_email_to = "ops@x.com"
    _, core, _ = _render_all(a)
    assert "STORAGE_BUCKET=b" in core
    assert "SMTP_HOST=smtp-relay.brevo.com" in core
    assert "NOTIFY_EMAIL_TO=ops@x.com" in core


def test_whatsapp_env_placeholders_and_verify_token():
    a = default_answers("demo")
    s, _, wa = _render_all(a)
    assert "WA_PHONE_ID=fill-me" in wa
    assert f"WA_VERIFY_TOKEN={s.wa_verify_token}" in wa
    assert "CORE_URL=http://localhost:8090" in wa


def test_admin_env_locale():
    a = default_answers("demo")
    a.locale = "en"
    assert "VITE_DEFAULT_LOCALE=en" in envfiles.render_admin_env(a)
