import dataclasses

import pytest

# The renderer modules are imported the way the game imports them (through
# the platform layer); imported on their own first, their import cycle breaks.
import backends.unix.system  # noqa: F401
from client.refresh import renderer


class Imports:
    """The renderer imports GetRefAPI uses."""

    def __init__(self) -> None:
        self.restart_requests = []

    def Vid_RequestRestart(self, value) -> None:  # noqa: N802
        self.restart_requests.append(value)


@pytest.mark.parametrize("module", ["client.refresh.gl1.gl1_main", "client.refresh.gl3.gl3_main"])
def test_renderers_provide_every_entry_point(module):
    import importlib
    main = importlib.import_module(module)
    imports = Imports()
    re = main.GetRefAPI(imports)
    assert isinstance(re, renderer.Renderer)
    assert re.api_version == renderer.API_VERSION
    for field in dataclasses.fields(renderer.Renderer):
        if field.name != "api_version":
            assert callable(getattr(re, field.name)), field.name
    assert len(imports.restart_requests) == 1  # the new restart API is announced
