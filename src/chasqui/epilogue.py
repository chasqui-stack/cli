"""The `chasqui new` closing message: how to run what was just generated."""

from chasqui.provision import StepResult
from chasqui.secrets_gen import GeneratedSecrets
from chasqui.wizard import Answers


def build(a: Answers, s: GeneratedSecrets, results: list[StepResult]) -> str:
    lines: list[str] = []
    failures = [r for r in results if not r.ok]

    lines.append(f"\n🎉 {a.slug} is ready.\n")

    if failures:
        lines.append("Pending steps (run them yourself, in this order):")
        for r in failures:
            lines.append(f"  - {r.manual_cmd}")
            if r.detail and not r.skipped:
                lines.append(f"      ({r.detail.splitlines()[-1]})")
        lines.append("")

    lines.append("Start the stack (one terminal each):")
    lines.append(f"  cd {a.slug}/core && make dev        # API on :{a.core_port}")
    if "whatsapp" in a.channels:
        lines.append(
            f"  cd {a.slug}/whatsapp && make dev    # WhatsApp gateway on :{a.gateway_port}"
        )
    if "telegram" in a.channels:
        lines.append(
            f"  cd {a.slug}/telegram && make dev    # Telegram gateway on :{a.telegram_port}"
        )
    if "web" in a.channels:
        lines.append(
            f"  cd {a.slug}/web && npm run dev      # web widget gateway on :{a.web_port}"
        )
    lines.append(
        f"  cd {a.slug}/admin && npm run dev    # panel on http://localhost:{a.admin_port}"
    )
    lines.append("")

    lines.append("Admin panel login:")
    lines.append(f"  {a.admin_email}")
    if not a.admin_password:
        lines.append(f"  password (generated): {s.admin_password}")
    lines.append("")

    if "whatsapp" in a.channels:
        lines.append("WhatsApp webhook (Meta app → WhatsApp → Configuration):")
        steps = []
        if not a.wa_configured:
            steps.append("Fill the WA_* credentials in whatsapp/.env")
        steps += [
            f"Expose the gateway: ngrok http {a.gateway_port}",
            "Set WA_CALLBACK_URL in whatsapp/.env to the ngrok https URL and "
            "restart the gateway (it registers the webhook itself)",
            f"Verify token (already in whatsapp/.env): {s.wa_verify_token}",
            "Full guide: https://github.com/chasqui-stack/chasqui/blob/main/docs/WHATSAPP-SETUP.md",
        ]
        lines += [f"  {i}. {step}" for i, step in enumerate(steps, start=1)]
        lines.append("")

    if "telegram" in a.channels:
        lines.append("Telegram webhook:")
        tg_steps = []
        if not a.tg_configured:
            tg_steps.append(
                "Get a bot token from @BotFather and set TELEGRAM_BOT_TOKEN in telegram/.env"
            )
        tg_steps += [
            f"Expose the gateway: ngrok http {a.telegram_port}",
            "Set TELEGRAM_WEBHOOK_URL in telegram/.env to <ngrok-url>/webhook and "
            "restart the gateway (it registers the webhook itself)",
            "Full guide: https://github.com/chasqui-stack/chasqui/blob/main/docs/TELEGRAM-SETUP.md",
        ]
        lines += [f"  {i}. {step}" for i, step in enumerate(tg_steps, start=1)]
        lines.append("")

    if "web" in a.channels:
        lines.append("Web widget (no webhook — replies stream over SSE, ADR-011):")
        web_steps = [
            f"Try it locally: open http://localhost:{a.web_port}/demo (demo page)",
            "Embed it anywhere on an allowed origin: "
            f'<script src="http://localhost:{a.web_port}/widget.js"></script>',
            f"Allowed origins live in web/.env: WEB_ALLOWED_ORIGINS={a.web_allowed_origins}",
        ]
        lines += [f"  {i}. {step}" for i, step in enumerate(web_steps, start=1)]
        lines.append("")

    lines.append("Everything the wizard wrote lives in each service's .env —")
    lines.append("LLM, embeddings*, storage, notifications are all swappable")
    lines.append("there. (*EMBEDDING_DIM is baked in at the first migrate.)")
    return "\n".join(lines)
