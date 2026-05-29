"""MFI CLI — command-line interface for Model-Free Intelligence."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .config import init_config, load_config, default_config_path
from .analyzer import analyze, print_corrections
from .patcher import propose_patches, print_proposals
from .evolution import run_evolution
from .dashboard import status as dashboard_status, print_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mfi",
        description="Model-Free Intelligence — evolution loop for AI agents",
        epilog=(
            "Scans session logs for user corrections, generates skill patches, "
            "and evolves the agent's knowledge automatically."
        ),
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"mfi {__version__}",
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        default=None,
        help="Config file path (default: ~/.mfi/config.json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize MFI configuration")

    # status
    p_status = subparsers.add_parser("status", help="Show evolution status")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Scan sessions for corrections")
    p_analyze.add_argument("--days", type=int, default=3, help="Days of session logs to scan (default: 3)")
    p_analyze.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    # propose
    p_propose = subparsers.add_parser("propose", help="Generate patch proposals from corrections")
    p_propose.add_argument("--days", type=int, default=3, help="Days of session logs to scan (default: 3)")
    p_propose.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    # evolve
    p_evolve = subparsers.add_parser("evolve", help="Run full evolution loop (analyze → propose → apply)")
    p_evolve.add_argument("--days", type=int, default=3, help="Days of session logs to scan (default: 3)")
    p_evolve.add_argument("--review", action="store_true", help="Review mode: propose patches but don't apply")
    p_evolve.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    return parser


def main(argv: Optional[list] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    config_path: Optional[Path] = args.config

    if args.command == "init":
        cfg = init_config(config_path)
        print(f"[mfi] initialized: {default_config_path() if not config_path else config_path}")
        return 0

    if args.command == "status":
        data = dashboard_status(config_path)
        print_status(data)
        return 0

    if args.command == "analyze":
        config = load_config(config_path)
        corrections = analyze(
            config=config,
            days=args.days,
        )
        print_corrections(corrections, verbose=args.verbose)
        return 0

    if args.command == "propose":
        config = load_config(config_path)
        corrections = analyze(config=config, days=args.days)
        if not corrections:
            print("[mfi] no corrections found")
            return 0
        proposals = propose_patches(corrections=corrections, config=config)
        print_proposals(proposals, verbose=args.verbose)
        return 0

    if args.command == "evolve":
        report = run_evolution(
            config_path=config_path,
            auto_apply=not args.review,
            days=args.days,
            verbose=args.verbose,
        )
        print()
        print(report.summary())
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
