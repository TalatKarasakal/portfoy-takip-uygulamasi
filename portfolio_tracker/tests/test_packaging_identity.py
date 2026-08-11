import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def _string_assignments(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                values[target.id] = node.value.value
    return values


def test_macos_packaging_uses_one_canonical_application_identity():
    values = _string_assignments(PROJECT_ROOT / "portfolio_tracker.spec")
    dmg_script = (PROJECT_ROOT / "packaging/macos/build_dmg.sh").read_text(
        encoding="utf-8"
    )
    workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )

    assert values["MACOS_BUNDLE_NAME"] == "Portföy Takip.app"
    assert values["MACOS_BUNDLE_IDENTIFIER"] == "com.talat.portfoytakip"
    assert 'app_name="Portföy Takip.app"' in dmg_script
    assert "dist/Portföy Takip.app/Contents/MacOS/PortfolioTracker" in workflow
