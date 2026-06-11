from chasqui import rename
from chasqui.wizard import default_answers


def test_rename_brands_deploy_and_db(mini_stack):
    a = default_answers("mi-agente")
    a.deploy_domain = "miagente.com"
    a.deploy_registry_user = "acme"
    a.deploy_server_ip = "198.51.100.7"

    touched = rename.apply(mini_stack, a)

    core_deploy = (mini_stack / "core" / "config" / "deploy.yml").read_text()
    assert "service: mi-agente-core" in core_deploy
    assert "image: acme/mi-agente-core" in core_deploy
    assert "198.51.100.7" in core_deploy and "203.0.113.10" not in core_deploy
    assert "api.miagente.com" in core_deploy
    assert "POSTGRES_DB: mi_agente" in core_deploy
    assert "-d mi_agente" in core_deploy

    wa_deploy = (mini_stack / "whatsapp" / "config" / "deploy.yml").read_text()
    assert "service: mi-agente-whatsapp" in wa_deploy
    assert "wsp.miagente.com" in wa_deploy
    assert 'CORE_URL: "https://api.miagente.com"' in wa_deploy

    assert '"name": "mi-agente-admin"' in (mini_stack / "admin" / "package.json").read_text()
    assert "DATABASE mi_agente" in (mini_stack / "core" / "config" / "init.sql").read_text()
    assert "core/config/deploy.yml" in touched


def test_rename_without_deploy_answers_keeps_placeholders(mini_stack):
    a = default_answers("demo")
    rename.apply(mini_stack, a)
    core_deploy = (mini_stack / "core" / "config" / "deploy.yml").read_text()
    assert "service: demo-core" in core_deploy
    assert "your-username" in core_deploy  # placeholder stays until they deploy
    assert "203.0.113.10" in core_deploy
