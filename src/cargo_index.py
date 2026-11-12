"""Читаем индекс Cargo по HTTP. Каждая строка индекса описывает релиз."""

from dataclasses import dataclass
import json
import re
from urllib.request import urlopen


@dataclass(frozen=True, order=True)
class Package:
    """Имя пакета и выбранная версия."""

    name: str
    version: str = ""

    def __str__(self):
        """Для тестового пакета достаточно имени, у него нет версии."""
        return f"{self.name}@{self.version}" if self.version else self.name


def index_path(name):
    """Собираем путь к записи пакета по правилам индекса Cargo."""
    name = name.lower()
    if len(name) < 3:
        return f"{len(name)}/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def stable_version(value):
    """Разбираем стабильную версию и отбрасываем метаданные сборки."""
    raw = value.split("+", 1)[0]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", raw):
        return None
    return tuple(map(int, raw.split(".")))


def caret_limit(parts):
    """Находим первую версию за пределами диапазона с ^."""
    first = next((i for i, n in enumerate(parts) if n), len(parts) - 1)
    return tuple(parts[:first]) + (parts[first] + 1,) + (0,) * (2 - first)


def matches_clause(version, clause):
    """Проверяем версию по одному условию из Cargo."""
    if clause in {"*", "x", "X"}:
        return True
    match = re.fullmatch(
        r"(>=|<=|>|<|=|\^|~)?\s*([0-9]+(?:\.[0-9]+){0,2})"
        r"(?:\.[*xX])?(?:\+[\w.-]+)?", clause)
    if not match:
        raise ValueError(f"unsupported Cargo requirement: {clause}")
    operator, raw = match.groups()
    parts = tuple(map(int, raw.split(".")))
    prefix = version[:len(parts)]
    floor = parts + (0,) * (3 - len(parts))
    if clause.endswith(("*", ".x", ".X")) or operator == "=":
        return prefix == parts
    if operator == "~":
        width = min(2, len(parts))
        return version >= floor and version[:width] == parts[:width]
    comparisons = {">": prefix > parts, ">=": prefix >= parts,
                   "<": prefix < parts, "<=": prefix <= parts}
    if operator in comparisons:
        return comparisons[operator]
    return floor <= version < caret_limit(parts)


class CargoRepository:
    """Читаем стабильные релизы и их обязательные зависимости."""

    def __init__(self, url):
        """Храним загруженные записи до конца запуска программы."""
        self.url = url
        self.cache = {}

    def records(self, name):
        """Читаем по одной записи JSON на строку и сохраняем их в кэше."""
        name = name.lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise ValueError(f"invalid crate name: {name}")
        if name not in self.cache:
            with urlopen(f"{self.url}/{index_path(name)}", timeout=20) as res:
                rows = [json.loads(line) for line in res if line.strip()]
            self.cache[name] = rows
        return self.cache[name]

    def resolve(self, name, requirement="*"):
        """Выбираем самый новый подходящий релиз среди неотозванных."""
        clauses = [part.strip() for part in requirement.split(",")]
        eligible = []
        for row in self.records(name):
            version = stable_version(row["vers"])
            if version is None or row["yanked"]:
                continue
            if all(matches_clause(version, part) for part in clauses):
                eligible.append((version, row["vers"]))
        if not eligible:
            raise ValueError(f"no stable release for {name} ({requirement})")
        return Package(name.lower(), max(eligible)[1])

    def dependencies(self, package, exclude=""):
        """Собираем обязательные зависимости для работы и сборки пакета."""
        row = next(row for row in self.records(package.name)
                   if row["vers"] == package.version)
        result = set()
        for dep in row["deps"]:
            name = dep.get("package") or dep["name"]
            if dep["kind"] == "dev" or dep["optional"]:
                continue
            if exclude and exclude in name:
                continue
            if dep.get("registry"):
                raise ValueError(f"external registry is unsupported: {name}")
            result.add(self.resolve(name, dep["req"]))
        return sorted(result)
