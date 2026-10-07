"""In-memory view of ``ui_context.json``: the nodes and relationships of the application UI."""

from __future__ import annotations

from typing import Any


class UiContext:
    """Nodes (consoles, screens, buttons, ...) and the transitions between them."""

    def __init__(self, raw: Any):
        self.raw: dict[str, Any] = raw if isinstance(raw, dict) else {}
        nodes = self.raw.get("nodes", []) or []
        relationships = self.raw.get("relationships", []) or []

        self.nodes = [node for node in nodes if isinstance(node, dict) and node.get("id")]
        self.node_ids = {str(node.get("id")) for node in self.nodes}
        self.node_names = {str(node.get("id")): str(node.get("name", "")) for node in self.nodes}
        self.relationships = [rel for rel in relationships if isinstance(rel, dict) and rel.get("to")]

    def name_of(self, node_id: str) -> str:
        return self.node_names.get(node_id, node_id)
