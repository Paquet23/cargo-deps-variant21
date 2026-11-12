"""Read and validate the YAML configuration."""

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlsplit

import yaml


@dataclass(frozen=True)
class Config:
    """Validated settings for the selected repository."""

    package: str
    repository: str
    test_mode: bool
    exclude: str


def load_config(path):
    """Read YAML and resolve a test path relative to its config."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    keys = {"package", "repository", "test_mode", "exclude"}
    if not isinstance(data, dict) or set(data) != keys:
        raise ValueError("expected exactly: " + ", ".join(sorted(keys)))
    package, source = data["package"], data["repository"]
    test, exclude = data["test_mode"], data["exclude"]
    if type(test) is not bool:
        raise ValueError("test_mode: expected true or false")
    if not isinstance(exclude, str):
        raise ValueError("exclude: expected a string")
    pattern = r"[A-Z]+" if test else r"[a-zA-Z0-9][a-zA-Z0-9_-]*"
    if not isinstance(package, str) or not re.fullmatch(pattern, package):
        raise ValueError("package: invalid name")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("repository: expected a URL or a file path")
    source = validate_source(source, path, test)
    return Config(package, source, test, exclude)


def validate_source(source, config_path, test):
    """Validate the repository address for the active mode."""
    if test:
        path = (config_path.parent / source).resolve()
        if not path.is_file():
            raise ValueError(f"repository: file not found: {path}")
        return str(path)
    url = urlsplit(source)
    if url.scheme not in {"http", "https"} or not url.hostname:
        raise ValueError("repository: expected an HTTP(S) URL")
    if url.query or url.fragment or url.username or url.password:
        raise ValueError("repository: expected a plain sparse index URL")
    return source.rstrip("/")
