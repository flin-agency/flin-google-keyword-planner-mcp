from pathlib import Path
import tomllib

from packaging.requirements import Requirement
from packaging.version import Version


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_mcp_dependency_excludes_incompatible_v2() -> None:
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    dependencies = [Requirement(value) for value in project["project"]["dependencies"]]
    mcp_requirement = next(
        requirement for requirement in dependencies if requirement.name == "mcp"
    )

    incompatible_v2_releases = ("2.0.0", "2.0.1", "2.1.0", "2.999.999")

    assert all(
        Version(version) not in mcp_requirement.specifier
        for version in incompatible_v2_releases
    )
