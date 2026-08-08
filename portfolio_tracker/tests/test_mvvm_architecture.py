import ast
from pathlib import Path

VIEWS_DIR = Path(__file__).parents[1] / "app" / "views"
FORBIDDEN_PREFIXES = ("app.database", "app.models", "app.services")


def test_views_do_not_import_models_database_or_services():
    violations = []
    for path in VIEWS_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(FORBIDDEN_PREFIXES):
                    violations.append(f"{path.name}:{node.lineno} {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_PREFIXES):
                        violations.append(f"{path.name}:{node.lineno} {alias.name}")
    assert violations == []


def test_views_do_not_own_threads():
    violations = []
    for path in VIEWS_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {"QThread", "QRunnable"}:
                violations.append(f"{path.name}:{node.lineno} {node.id}")
    assert violations == []
