"""
Lighthouse CLI - Command line interface for managing Lighthouse daemon.

Provides commands for:
- Configuration validation
- Daemon management (start, status)
- Watcher management (list, trigger)
- Manual notifications
- API key generation for webhooks
"""

import argparse
import secrets
import sys
from pathlib import Path

from lighthouse.config import load_config
from lighthouse.coordinator import create_watcher_coordinator
from lighthouse.core import AlertDecision
from lighthouse.daemon import LighthouseDaemon
from lighthouse.logging_config import get_logger

logger = get_logger(__name__)


def cmd_config_validate(args: argparse.Namespace) -> int:
    """Validate configuration file."""
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        config = load_config(str(config_path))
        print(f"✓ Configuration valid: {config_path}")
        print(f"  - {len(config.watchers)} watcher(s) configured")
        print(f"  - {len(config.notifiers)} notifier(s) configured")
        print(f"  - State directory: {config.state_dir}")
        return 0
    except Exception as e:
        print(f"✗ Configuration invalid: {e}", file=sys.stderr)
        return 1


def cmd_daemon_start(args: argparse.Namespace) -> int:
    """Start the Lighthouse daemon."""
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        print(f"Starting Lighthouse daemon with config: {config_path}")
        daemon = LighthouseDaemon(str(config_path))
        daemon.start()
        return 0
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    except Exception as e:
        print(f"Error starting daemon: {e}", file=sys.stderr)
        return 1


def cmd_watcher_list(args: argparse.Namespace) -> int:
    """List all configured watchers."""
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        config = load_config(str(config_path))
        print(f"Configured watchers ({len(config.watchers)}):\n")

        for i, watcher in enumerate(config.watchers, 1):
            print(f"{i}. {watcher.name}")
            print(f"   Observer:  {watcher.observer.type}")
            print(f"   Trigger:   {watcher.trigger.type}")
            print(f"   Evaluator: {watcher.evaluator.type}")
            if watcher.priority is not None:
                print(f"   Priority:  {watcher.priority}")
            print()

        return 0
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1


def cmd_watcher_trigger(args: argparse.Namespace) -> int:
    """Manually trigger a specific watcher."""
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        config = load_config(str(config_path))

        # Find the watcher
        watcher_config = None
        for watcher in config.watchers:
            if watcher.name == args.name:
                watcher_config = watcher
                break

        if not watcher_config:
            print(f"Error: Watcher '{args.name}' not found", file=sys.stderr)
            print("\nAvailable watchers:", file=sys.stderr)
            for watcher in config.watchers:
                print(f"  - {watcher.name}", file=sys.stderr)
            return 1

        # Create coordinator
        print(f"Triggering watcher: {args.name}")

        def on_alert(name: str, decision: AlertDecision, priority: int | None) -> None:
            if decision.should_alert:
                print(f"\n✗ Alert triggered for '{name}':")
                print(f"  Severity: {decision.severity}")
                print(f"  Message:  {decision.message}")
            else:
                print(f"\n✓ No alert needed for '{name}'")

        coordinator = create_watcher_coordinator(
            watcher_config=watcher_config,
            state_dir=config.state_dir,
            on_alert=on_alert
        )

        # Run the check
        decision = coordinator.check()

        if decision:
            # Alert was triggered, notify via configured notifiers
            if not args.dry_run:
                from lighthouse.plugins import create_notifier
                print("\nSending notifications...")
                for notifier_config in config.notifiers:
                    try:
                        notifier = create_notifier(
                            notifier_config.type,
                            notifier_config.config
                        )
                        success = notifier.notify(decision, watcher_config.name)
                        status = "✓" if success else "✗"
                        print(f"  {status} {notifier_config.type}")
                    except Exception as e:
                        print(f"  ✗ {notifier_config.type}: {e}")
            else:
                print("\n(Dry run - notifications not sent)")

        return 0

    except Exception as e:
        print(f"Error triggering watcher: {e}", file=sys.stderr)
        logger.exception("Error in watcher trigger")
        return 1


def cmd_api_key_generate(args: argparse.Namespace) -> int:
    """Generate a new API key for webhook authentication."""
    # Generate cryptographically secure key
    api_key = secrets.token_hex(args.length)

    if args.output:
        # Append to file
        output_path = Path(args.output)
        try:
            # Create parent directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "a", encoding="utf-8") as f:
                f.write(f"{api_key}\n")

            print(f"✓ API key appended to: {output_path}", file=sys.stderr)
            print(f"  Key preview: {api_key[:16]}...{api_key[-16:]}", file=sys.stderr)
            return 0
        except Exception as e:
            print(f"✗ Error writing to file: {e}", file=sys.stderr)
            return 1

    # Print to stdout
    print(api_key)
    return 0


def cmd_notify(args: argparse.Namespace) -> int:
    """Send a manual notification."""
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        from lighthouse.core import AlertDecision
        from lighthouse.plugins import create_notifier

        config = load_config(str(config_path))

        # Create alert decision
        decision = AlertDecision(
            should_alert=True,
            severity=args.severity,
            message=args.message,
            context={"manual": True, "title": args.title}
        )

        print(f"Sending notification: {args.title}")
        print(f"Message: {args.message}")
        print(f"Severity: {args.severity}\n")

        sent_count = 0
        for notifier_config in config.notifiers:
            try:
                notifier = create_notifier(
                    notifier_config.type,
                    notifier_config.config
                )
                # Use title as watcher name
                success = notifier.notify(decision, args.title)
                status = "✓" if success else "✗"
                print(f"  {status} {notifier_config.type}")
                if success:
                    sent_count += 1
            except Exception as e:
                print(f"  ✗ {notifier_config.type}: {e}")

        print(f"\nSent to {sent_count}/{len(config.notifiers)} notifier(s)")
        return 0 if sent_count > 0 else 1

    except Exception as e:
        print(f"Error sending notification: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="lighthouse",
        description="Lighthouse - Intelligent monitoring and notification system"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Config commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(dest="subcommand")
    config_subparsers.add_parser("validate", help="Validate configuration file")

    # API key commands
    api_parser = subparsers.add_parser("api-key", help="API key management")
    api_subparsers = api_parser.add_subparsers(dest="subcommand")

    generate_parser = api_subparsers.add_parser("generate", help="Generate a new API key")
    generate_parser.add_argument(
        "-o", "--output",
        type=str,
        help="File to append the API key to (prints to stdout if not specified)"
    )
    generate_parser.add_argument(
        "-l", "--length",
        type=int,
        default=32,
        help="Length of key in bytes (default: 32, produces 64 hex chars)"
    )

    # Daemon commands
    daemon_parser = subparsers.add_parser("daemon", help="Daemon management")
    daemon_subparsers = daemon_parser.add_subparsers(dest="subcommand")
    daemon_subparsers.add_parser("start", help="Start daemon (foreground)")

    # Watcher commands
    watcher_parser = subparsers.add_parser("watcher", help="Watcher management")
    watcher_subparsers = watcher_parser.add_subparsers(dest="subcommand")
    watcher_subparsers.add_parser("list", help="List all configured watchers")

    trigger_parser = watcher_subparsers.add_parser("trigger", help="Manually trigger a watcher")
    trigger_parser.add_argument("name", help="Name of watcher to trigger")
    trigger_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run check without sending notifications"
    )

    # Notify command
    notify_parser = subparsers.add_parser("notify", help="Send manual notification")
    notify_parser.add_argument("title", help="Notification title")
    notify_parser.add_argument("message", help="Notification message")
    notify_parser.add_argument(
        "-s", "--severity",
        choices=["low", "medium", "high", "critical"],
        default="medium",
        help="Severity level (default: medium)"
    )

    args = parser.parse_args()

    # Handle no command
    if not args.command:
        parser.print_help()
        return 0

    # Route to appropriate handler
    if args.command == "config":
        if args.subcommand == "validate":
            return cmd_config_validate(args)
        parser.print_help()
        return 0

    if args.command == "api-key":
        if args.subcommand == "generate":
            return cmd_api_key_generate(args)
        parser.print_help()
        return 0

    if args.command == "daemon":
        if args.subcommand == "start":
            return cmd_daemon_start(args)
        parser.print_help()
        return 0

    if args.command == "watcher":
        if args.subcommand == "list":
            return cmd_watcher_list(args)
        if args.subcommand == "trigger":
            return cmd_watcher_trigger(args)
        parser.print_help()
        return 0

    if args.command == "notify":
        return cmd_notify(args)

    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
