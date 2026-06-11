import pytest

from chasqui import module_gen


def test_generate_basic_module(mini_stack):
    created = module_gen.generate("price_check", cwd=mini_stack)

    init = mini_stack / "core" / "app" / "modules" / "price_check" / "__init__.py"
    assert init in created
    src = init.read_text()
    assert "class PriceCheckModule:" in src
    assert 'name = "price_check"' in src
    assert "async def price_check(" in src
    assert "module = PriceCheckModule()" in src
    assert "register_models" not in src
    assert "register_admin_routes" not in src

    test_file = mini_stack / "core" / "tests" / "modules" / "test_price_check.py"
    assert test_file in created
    assert "test_module_contract" in test_file.read_text()


def test_generate_with_models_and_admin(mini_stack):
    created = module_gen.generate(
        "inventory", cwd=mini_stack, with_models=True, with_admin=True
    )
    names = {p.name for p in created}
    assert {"__init__.py", "models.py", "admin.py", "test_inventory.py"} <= names

    src = (mini_stack / "core" / "app" / "modules" / "inventory" / "__init__.py").read_text()
    assert "def register_models(self):" in src
    assert "def register_admin_routes(self, router):" in src
    models = (mini_stack / "core" / "app" / "modules" / "inventory" / "models.py").read_text()
    assert "class InventoryRecord(SQLModel, table=True):" in models
    assert "make makemigrations" in models


def test_generate_runs_from_inside_core(mini_stack):
    module_gen.generate("hello", cwd=mini_stack / "core")
    assert (mini_stack / "core" / "app" / "modules" / "hello" / "__init__.py").exists()


def test_generate_rejects_bad_names_and_duplicates(mini_stack):
    with pytest.raises(module_gen.ModuleGenError):
        module_gen.generate("Bad-Name", cwd=mini_stack)
    module_gen.generate("dupe", cwd=mini_stack)
    with pytest.raises(module_gen.ModuleGenError):
        module_gen.generate("dupe", cwd=mini_stack)


def test_generate_outside_a_project_fails(tmp_path):
    with pytest.raises(module_gen.ModuleGenError):
        module_gen.generate("hello", cwd=tmp_path)
