"""Command line interface for the Cargo dependency graph."""

import argparse
from dataclasses import asdict
import sys

import yaml

from config import load_config


def main(argv=None):
    """Validate the configuration and print the requested result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="YAML config path")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        for key, value in asdict(config).items():
            print(f"{key}={value}")
    except (ValueError, OSError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
