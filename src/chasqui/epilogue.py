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

    lines.append("Start the stack (three terminals):")
    lines.append(f"  cd {a.slug}/core && make dev        # API on :8090")
    lines.append(f"  cd {a.slug}/whatsapp && make dev    # gateway on :8000")
    lines.append(f"  cd {a.slug}/admin && npm run dev    # panel on http://localhost:5191")
    lines.append("")

    lines.append("Admin panel login:")
    lines.append(f"  {a.admin_email}")
    if not a.admin_password:
        lines.append(f"  password (generated): {s.admin_password}")
    lines.append("")

    lines.append("WhatsApp webhook (Meta app → WhatsApp → Configuration):")
    steps = []
    if not a.wa_configured:
        steps.append("Fill the WA_* credentials in whatsapp/.env")
    steps += [
        "Expose the gateway: ngrok http 8000",
        "Callback URL: the ngrok https URL (or set WA_CALLBACK_URL in whatsapp/.env)",
        f"Verify token (already in whatsapp/.env): {s.wa_verify_token}",
    ]
    lines += [f"  {i}. {step}" for i, step in enumerate(steps, start=1)]
    lines.append("")

    lines.append("Everything the wizard wrote lives in core/.env, whatsapp/.env and")
    lines.append("admin/.env — LLM, embeddings*, storage, notifications are all")
    lines.append("swappable there. (*EMBEDDING_DIM is baked in at the first migrate.)")
    return "\n".join(lines)
