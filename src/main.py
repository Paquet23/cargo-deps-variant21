"""Command line interface for the Cargo dependency graph."""

import argparse
from dataclasses import asdict
import sys

import yaml

from cargo_index import CargoRepository
from config import load_config


def main(argv=None):
    """Validate the configuration and print the requested result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="YAML config path")
    parser.add_argument("--mode", choices=("config", "direct"),
                        default="direct")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.mode == "config":
            for key, value in asdict(config).items():
                print(f"{key}={value}")
        elif config.test_mode:
            raise ValueError("test repositories are added in stage 3")
        else:
            repo = CargoRepository(config.repository)
            for dep in repo.dependencies(repo.resolve(config.package)):
                print(dep)
    except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
