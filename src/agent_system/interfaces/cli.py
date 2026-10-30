"""Initial CLI; operational commands are not implemented yet."""

import argparse
import json

from agent_system import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ams")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Report the software implementation stage")
    args = parser.parse_args(argv)
    if args.command == "status":
        print(json.dumps({
            "version": __version__,
            "stage": "foundation",
            "operational": False,
            "message": "Installer, persistence and execution are not implemented.",
        }))
        return 0
    return 2
