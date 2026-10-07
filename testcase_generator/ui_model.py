"""In-memory view of ``ui_context.json``: the nodes and relationships of the application UI."""

from __future__ import annotations

import re
from collections import Counter
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

        self._parents = {str(node.get("id")): node.get("parent") for node in self.nodes}
        self.console_names = {
            str(node.get("id")): str(node.get("name", "")) for node in self.nodes if node.get("type") == "console"
        }

        # Names that identify exactly one node, longest first, so that a longer
        # name is matched before a shorter name contained in it.
        name_counts = Counter(self.node_names.values())
        unique = [(node_id, name) for node_id, name in self.node_names.items() if name and name_counts[name] == 1]
        unique.sort(key=lambda entry: len(entry[1]), reverse=True)
        self._name_patterns = [
            (node_id, re.compile(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])")) for node_id, name in unique
        ]

    def name_of(self, node_id: str) -> str:
        return self.node_names.get(node_id, node_id)

    def console_of(self, node_id: str) -> str | None:
        """The console a node belongs to, found by following the parent links."""
        seen = set()
        current: Any = node_id
        while current and current not in seen:
            if current in self.console_names:
                return current
            seen.add(current)
            current = self._parents.get(current)
        return None

    def nodes_named_in(self, text: str) -> list[str]:
        """IDs of all nodes whose name occurs in ``text`` as whole words.

        The match is case-sensitive: names such as "Calendar" or "Performance"
        are also ordinary words ("a calendar date"), which must not count.
        """
        remaining = text or ""
        found = []
        for node_id, pattern in self._name_patterns:
            if pattern.search(remaining):
                found.append(node_id)
                remaining = pattern.sub(" ", remaining)
        return found
