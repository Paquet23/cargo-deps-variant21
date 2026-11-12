"""Проверяем настройки, выбор версий, обход графа и вывод."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cargo_index import index_path, matches_clause
from config import load_config
from graph import TestRepository, build_graph, load_order
from plantuml import render


class AnalyzerTests(unittest.TestCase):
    """Проверяем обход на небольших графах с известным результатом."""

    def setUp(self):
        """Загружаем тот же тестовый граф, что и в примерах запуска."""
        self.repo = TestRepository(ROOT / "examples/test-repo.yaml")

    def test_diamond_and_order(self):
        """Общая зависимость встречается один раз, раньше обоих пакетов."""
        graph = build_graph(self.repo, "A", "")
        self.assertEqual(len(graph.edges), 5)
        self.assertFalse(graph.cycles)
        self.assertEqual(list(map(str, load_order(graph))),
                         ["D", "B", "E", "C", "A"])

    def test_filter_prunes_branch(self):
        """Фильтр убирает ветвь, но общий потомок доступен по другому пути."""
        graph = build_graph(self.repo, "A", "C")
        self.assertEqual(set(map(str, graph.edges)), {"A", "B", "D"})
        self.assertFalse(build_graph(self.repo, "A", "A").edges)

    def test_cycles(self):
        """Цикл виден на диаграмме, а порядок загрузки для него невозможен."""
        for root in ("F", "J"):
            graph = build_graph(self.repo, root, "")
            self.assertEqual(len(graph.cycles), 1)
            self.assertIn("-[#red]->", render(graph))
            with self.assertRaisesRegex(ValueError, "no load order"):
                load_order(graph)

    def test_leaf_and_cli(self):
        """По умолчанию программа рисует даже пакет без зависимостей."""
        result = subprocess.run(
            [sys.executable, "src/main.py", "examples/leaf.yaml"],
            cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertIn('rectangle "I"', result.stdout)
        self.assertIn("@enduml", result.stdout)
        self.assertNotIn("-->", result.stdout)

    def test_config_errors(self):
        """Ошибочные настройки обнаруживаются до начала анализа."""
        valid = ("package: A\nrepository: test-repo.yaml\n"
                 'test_mode: true\nexclude: ""\n')
        edits = [("package: A", "package: 42", "package"),
                 ("test-repo.yaml", "missing.yaml", "repository"),
                 ("true", '"true"', "test_mode"),
                 ('exclude: ""', "exclude: false", "exclude")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            (path.parent / "test-repo.yaml").write_text("A: []")
            for before, after, key in edits:
                with self.subTest(key=key):
                    path.write_text(valid.replace(before, after))
                    with self.assertRaisesRegex(ValueError, key):
                        load_config(path)

    def test_index_paths_and_constraints(self):
        """Проверяем пути индекса и условия выбора стабильных версий."""
        self.assertEqual([index_path(n) for n in ("a", "ab", "abc", "Serde")],
                         ["1/a", "2/ab", "3/a/abc", "se/rd/serde"])
        for version, req, expected in [
            ((1, 8, 0), "1.2", True), ((2, 0, 0), "1.2", False),
            ((0, 3, 0), "^0.2", False), ((0, 0, 2), "^0.0.1", False),
            ((1, 2, 8), "~1.2", True), ((1, 3, 0), "~1.2", False),
            ((1, 2, 9), "1.2.*", True), ((1, 2, 0), "<1.2", False),
        ]:
            with self.subTest(req=req, version=version):
                self.assertEqual(matches_clause(version, req), expected)


if __name__ == "__main__":
    unittest.main()
