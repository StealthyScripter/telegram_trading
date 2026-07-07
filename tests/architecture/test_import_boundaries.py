import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_DIRS = [
    "ingestion",
    "parsing",
    "decision",
    "risk",
    "capital",
    "execution",
    "events",
    "learning",
    "dashboard",
    "controls",
    "storage",
    "orchestration",
]


def production_files(package: str):
    return [
        path for path in (ROOT / package).rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def assert_no_forbidden_imports(package: str, forbidden: tuple[str, ...]):
    violations = []
    for path in production_files(package):
        for imported in imports_for(path):
            if imported.startswith(forbidden):
                violations.append((str(path.relative_to(ROOT)), imported))

    assert violations == []


def test_execution_import_boundary():
    assert_no_forbidden_imports(
        "execution",
        (
            "ingestion",
            "parsing",
            "decision",
            "risk",
            "capital",
            "learning",
            "signals",
            "brokers",
        ),
    )


def test_parsing_import_boundary():
    assert_no_forbidden_imports(
        "parsing",
        ("execution", "brokers", "risk", "capital", "decision", "learning"),
    )


def test_risk_import_boundary():
    assert_no_forbidden_imports(
        "risk",
        ("ingestion", "parsing", "execution", "brokers", "learning", "signals"),
    )


def test_capital_import_boundary():
    assert_no_forbidden_imports(
        "capital",
        ("ingestion", "parsing", "execution.brokers", "brokers", "decision.ml_model", "signals"),
    )


def test_decision_import_boundary():
    assert_no_forbidden_imports("decision", ("execution", "brokers"))


def test_learning_import_boundary():
    assert_no_forbidden_imports("learning", ("execution", "brokers"))


def test_dashboard_controls_import_boundary():
    assert_no_forbidden_imports("dashboard", ("execution.brokers", "brokers"))
    assert_no_forbidden_imports("controls", ("execution.brokers.oanda", "brokers.oanda"))


def test_production_modules_do_not_import_tests():
    for package in PRODUCTION_DIRS:
        assert_no_forbidden_imports(package, ("tests",))
