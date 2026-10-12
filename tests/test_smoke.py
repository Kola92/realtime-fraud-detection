import importlib

import pytest


@pytest.mark.parametrize("name", ["core", "producer", "scorer", "api"])
def test_subpackage_imports(name):
    importlib.import_module(f"fraudsvc.{name}")
