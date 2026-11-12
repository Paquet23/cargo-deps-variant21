"""Command line interface for the Cargo dependency graph."""

import argparse
from dataclasses import asdict
import sys

import yaml

from cargo_index import CargoRepository
from config import load_config
from graph import TestRepository, build_graph


def display(config, mode):
    """Run the requested analysis mode."""
    if mode == "config":
        for key, value in asdict(config).items():
            print(f"{key}={value}")
        return
    repo_type = TestRepository if config.test_mode else CargoRepository
    repo = repo_type(config.repository)
    if mode == "direct":
        if not config.exclude or config.exclude not in config.package:
            root = repo.resolve(config.package)
            for dep in repo.dependencies(root, config.exclude):
                print(dep)
        return
    graph = build_graph(repo, config.package, config.exclude)
    for node, children in graph.edges.items():
        print(f"{node}: {', '.join(map(str, children))}")
    for source, target in graph.cycles:
        print(f"Cycle edge: {source} -> {target}", file=sys.stderr)


def main(argv=None):
    """Validate the configuration and print the requested result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="YAML config path")
    parser.add_argument("--mode", choices=("config", "direct", "graph"),
                        default="graph")
    args = parser.parse_args(argv)
    try:
        display(load_config(args.config), args.mode)
    except (ValueError, OSError, KeyError, TypeError, RecursionError,
            yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
