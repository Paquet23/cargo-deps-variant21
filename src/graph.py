"""Строим граф зависимостей рекурсивным обходом в глубину."""

from dataclasses import dataclass, field
import re

import yaml

from cargo_index import Package


class TestRepository:
    """Тестовый граф, в котором связи перечислены в YAML."""

    def __init__(self, path):
        """Читаем связи и проверяем, что все указанные пакеты существуют."""
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
        """Имя тестового пакета состоит из заглавных латинских букв."""
        return isinstance(name, str) and re.fullmatch(r"[A-Z]+", name)

    def resolve(self, name):
        """Ищем тестовый пакет по имени."""
        if name not in self.rows:
            raise ValueError(f"test package not found: {name}")
        return Package(name)

    def dependencies(self, package, exclude=""):
        """Убираем совпадения с фильтром, повторы и сортируем имена."""
        return [Package(name) for name in sorted(set(self.rows[package.name]))
                if not exclude or exclude not in name]


@dataclass
class Graph:
    """Списки зависимостей и рёбра, на которых обнаружены циклы."""

    edges: dict = field(default_factory=dict)
    cycles: list = field(default_factory=list)


def build_graph(repo, name, exclude):
    """Обходим только пакеты, достижимые из выбранного пакета."""
    graph = Graph()
    active = set()

    def visit(node):
        """Раскрываем пакет один раз. Переход к предку замыкает цикл."""
        active.add(node)
        children = repo.dependencies(node, exclude)
        graph.edges[node] = children
        for child in children:
            # В active только пакеты из текущей цепочки вызовов.
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


def load_order(graph):
    """Обходим граф так, чтобы зависимости попадали в список первыми."""
    if graph.cycles:
        source, target = graph.cycles[0]
        raise ValueError(f"no load order: cycle edge {source} -> {target}")
    seen = set()
    result = []

    def visit(node):
        """Добавляем пакет в список после обхода его зависимостей."""
        if node in seen:
            return
        seen.add(node)
        for child in graph.edges[node]:
            visit(child)
        # К этому моменту все зависимости уже добавлены в результат.
        result.append(node)

    for node in graph.edges:
        visit(node)
    return result
