from pathlib import Path

from src.config import ROOT as CONFIG_ROOT
from src.quality import ROOT as QUALITY_ROOT


def test_runtime_resource_roots_are_the_databricks_directory():
    assert (CONFIG_ROOT / "config" / "migration.yml").is_file()
    assert (QUALITY_ROOT / "config" / "quality_mapping.yml").is_file()


def test_notebooks_support_workspace_filesystem_path_prefix():
    notebook_dir = Path(__file__).resolve().parents[1] / "notebooks"
    for notebook in notebook_dir.glob("*.py"):
        source = notebook.read_text(encoding="utf-8")
        assert 'candidate_dirs.append(f"/Workspace{relative_project_dir}")' in source
        assert 'Path(directory) / "src" / "config.py"' in source


def test_interactive_notebooks_reload_changed_project_modules_after_git_pull():
    notebook_dir = Path(__file__).resolve().parents[1] / "notebooks"
    for name, module in (("02_silver.py", "silver_module"), ("03_quality.py", "quality_module")):
        source = (notebook_dir / name).read_text(encoding="utf-8")
        assert f"importlib.reload({module})" in source
