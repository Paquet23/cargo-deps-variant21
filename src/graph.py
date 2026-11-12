"""Recursive DFS over a repository of dependencies."""

from dataclasses import dataclass, field
import re

import yaml

from cargo_index import Package


class TestRepository:
    """An explicitly described graph stored in YAML."""

    def __init__(self, path):
        """Read adjacency lists and validate every referenced name."""
        from pathlib import Path

        self.rows = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(self.rows, dict):
            raise ValueError("test repository: expected an adjacency map")
        for name, deps in self.rows.items():
            if not self.valid_name(name) or not isinstance(deps, list):
                raise ValueError(f"invalid test node: {name}")
            for dep in deps:
                if not self.valid_name(dep) or dep not in self.rows:
                    raise ValueError(f"unknown test dependency: {dep}")

    @staticmethod
    def valid_name(name):
        """Allow only uppercase Latin letters in test package names."""
        return isinstance(name, str) and re.fullmatch(r"[A-Z]+", name)

    def resolve(self, name):
        """Find a named test package."""
        if name not in self.rows:
            raise ValueError(f"test package not found: {name}")
        return Package(name)

    def dependencies(self, package, exclude=""):
        """Return the sorted direct dependencies after filtering."""
        return [Package(name) for name in sorted(set(self.rows[package.name]))
                if not exclude or exclude not in name]


@dataclass
class Graph:
    """Adjacency map plus detected back edges."""

    edges: dict = field(default_factory=dict)
    cycles: list = field(default_factory=list)


def build_graph(repo, name, exclude):
    """Traverse reachable nodes with recursive DFS and retain back edges."""
    graph = Graph()
    active = set()

    def visit(node):
        """Expand each node once and detect edges to active ancestors."""
        active.add(node)
        children = repo.dependencies(node, exclude)
        graph.edges[node] = children
        for child in children:
            if child in active:
                graph.cycles.append((node, child))
            elif child not in graph.edges:
                visit(child)
        active.remove(node)

    if exclude and exclude in name:
        return graph
    root = repo.resolve(name)
    if not exclude or exclude not in root.name:
        visit(root)
    return graph
