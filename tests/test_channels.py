"""Channel selection: which gateways get fetched + their .env wiring."""

from chasqui import envfiles, fetch
from chasqui.secrets_gen import GeneratedSecrets
from chasqui.wizard import default_answers


def test_default_is_whatsapp_only():
    a = default_answers("demo")
    assert a.channels == ["whatsapp"]
    core = envfiles.render_core_env(a, GeneratedSecrets())
    assert "CHANNEL_WHATSAPP_SEND_URL=" in core
    assert "CHANNEL_TELEGRAM_SEND_URL=" not in core


def test_telegram_channel_env_and_send_url():
    a = default_answers("demo")
    a.channels = ["telegram"]
    s = GeneratedSecrets()
    core = envfiles.render_core_env(a, s)
    tg = envfiles.render_telegram_env(a, s)
    assert "CHANNEL_TELEGRAM_SEND_URL=http://localhost:8001/send" in core
    assert "CHANNEL_WHATSAPP_SEND_URL=" not in core
    assert "TELEGRAM_BOT_TOKEN=fill-me" in tg
    assert f"TELEGRAM_WEBHOOK_SECRET={s.telegram_webhook_secret}" in tg
    # The shared secret is byte-identical across core and gateway (ADR-005)
    assert f"INTERNAL_API_KEY={s.internal_api_key}" in tg
    assert "PORT=8001" in tg
    assert f"CORE_URL=http://localhost:{a.core_port}" in tg


def test_both_channels_emit_both_send_urls():
    a = default_answers("demo")
    a.channels = ["whatsapp", "telegram"]
    core = envfiles.render_core_env(a, GeneratedSecrets())
    assert "CHANNEL_WHATSAPP_SEND_URL=" in core
    assert "CHANNEL_TELEGRAM_SEND_URL=" in core


def test_dirs_for_includes_only_selected_channels():
    assert set(fetch._dirs_for(["whatsapp"])) == {"core", "admin", "whatsapp"}
    assert set(fetch._dirs_for(["telegram"])) == {"core", "admin", "telegram"}
    assert set(fetch._dirs_for(["whatsapp", "telegram"])) == {
        "core", "admin", "whatsapp", "telegram",
    }
    # None falls back to WhatsApp (back-compat with the old single-channel flow)
    assert set(fetch._dirs_for(None)) == {"core", "admin", "whatsapp"}
