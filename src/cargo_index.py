"""Read Cargo's sparse JSON-lines index over HTTP."""

from dataclasses import dataclass
import json
import re
from urllib.request import urlopen


@dataclass(frozen=True, order=True)
class Package:
    """A resolved package version."""

    name: str
    version: str = ""

    def __str__(self):
        """Print versions only for registry packages."""
        return f"{self.name}@{self.version}" if self.version else self.name


def index_path(name):
    """Return the index path specified by Cargo's sparse protocol."""
    name = name.lower()
    if len(name) < 3:
        return f"{len(name)}/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def stable_version(value):
    """Parse a stable version and discard build metadata."""
    raw = value.split("+", 1)[0]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", raw):
        return None
    return tuple(map(int, raw.split(".")))


def caret_limit(parts):
    """Return the exclusive upper bound of a caret requirement."""
    first = next((i for i, n in enumerate(parts) if n), len(parts) - 1)
    return tuple(parts[:first]) + (parts[first] + 1,) + (0,) * (2 - first)


def matches_clause(version, clause):
    """Match one stable-version comparator in Cargo syntax."""
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
    """Read stable non-yanked releases and their mandatory dependencies."""

    def __init__(self, url):
        """Cache index entries within one invocation."""
        self.url = url
        self.cache = {}

    def records(self, name):
        """Download a crate's newline-delimited index once."""
        name = name.lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise ValueError(f"invalid crate name: {name}")
        if name not in self.cache:
            with urlopen(f"{self.url}/{index_path(name)}", timeout=20) as res:
                rows = [json.loads(line) for line in res if line.strip()]
            self.cache[name] = rows
        return self.cache[name]

    def resolve(self, name, requirement="*"):
        """Choose the newest stable version satisfying the requirement."""
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
        """Resolve required normal and build dependencies of one release."""
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
