"""`_find_station_root` against fake address spaces.

The DEMO_SAS path `Objects/Root/EVN/RLDC/PROJECT/SAS` embeds the project name,
so pointing Black Interface at a DataServer with a *different* project loaded
was the first known break. These tests pin the fix: the root is found by what
it contains (voltage-level children), not by what it is called.
"""

from __future__ import annotations

import pytest
from asyncua import ua

from blackinterface.integration.opcua.discovery import _find_station_root


class FakeQualifiedName:
    def __init__(self, name: str, namespace: int) -> None:
        self.Name = name
        self.NamespaceIndex = namespace


class FakeNodeId:
    def __init__(self, identifier: str) -> None:
        self._identifier = identifier

    def to_string(self) -> str:
        return f"ns=2;s={self._identifier}"


class FakeNode:
    def __init__(
        self,
        name: str,
        *children: FakeNode,
        namespace: int = 2,
        node_class: ua.NodeClass = ua.NodeClass.Object,
    ) -> None:
        self._name = name
        self._namespace = namespace
        self._node_class = node_class
        self._children = list(children)
        self.nodeid = FakeNodeId(name)

    async def get_children(self) -> list[FakeNode]:
        return self._children

    async def read_browse_name(self) -> FakeQualifiedName:
        return FakeQualifiedName(self._name, self._namespace)

    async def read_node_class(self) -> ua.NodeClass:
        return self._node_class

    async def get_child(self, path: list[str]) -> FakeNode:
        raise ua.UaStatusCodeError(ua.StatusCodes.BadNoMatch)


class FakeClient:
    def __init__(self, objects: FakeNode) -> None:
        self.nodes = type("Nodes", (), {"objects": objects})()


def _station(name: str) -> FakeNode:
    return FakeNode(name, FakeNode("500kV"), FakeNode("220kV"), FakeNode("Subs"))


async def test_finds_a_station_under_project_specific_grouping_nodes() -> None:
    """Not RLDC, not PROJECT, not SAS — different names, same shape."""
    objects = FakeNode(
        "Objects",
        FakeNode("Server", namespace=0),  # the standard namespace is never ours
        FakeNode("OADataModel", FakeNode("ModelName", node_class=ua.NodeClass.Variable)),
        FakeNode(
            "Root", FakeNode("EVN", FakeNode("NLDC", FakeNode("TramB", _station("STATION_B"))))
        ),
    )
    found = await _find_station_root(FakeClient(objects))
    assert (await found.read_browse_name()).Name == "STATION_B"


async def test_a_station_directly_under_objects_is_found() -> None:
    objects = FakeNode("Objects", _station("SAS"))
    found = await _find_station_root(FakeClient(objects))
    assert (await found.read_browse_name()).Name == "SAS"


async def test_no_station_anywhere_raises_a_diagnosable_error() -> None:
    objects = FakeNode("Objects", FakeNode("Root", FakeNode("EVN", FakeNode("Empty"))))
    with pytest.raises(LookupError, match="voltage-level"):
        await _find_station_root(FakeClient(objects))
