import pytest

from databricks.src.config import load_config


def test_workspace_name_is_config_driven():
    config = load_config(environ={"PANGANWATCH_CATALOG": "sandbox_catalog"})
    assert config.qualified("silver", "harga_pangan") == "sandbox_catalog.pw_silver.harga_pangan"
    assert config.volume_path == "/Volumes/sandbox_catalog/pw_landing/snapshots"


def test_rejects_unsafe_catalog_identifier():
    with pytest.raises(ValueError):
        load_config(environ={"PANGANWATCH_CATALOG": "main; DROP TABLE x"})
