"""Private weather recovery commands; mutations enqueue work, never call Apify."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from .canonical import encode
from .errors import Conflict, PlanningError
from .execution_control import ExecutionControl
from .execution_identity import storage_binding
from .records import Actor
from .runtime_config import RuntimeConfig
from .weather_operator import WeatherOperator
from .workspace import Workspace

LOG = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--run-id", required=True)
    for action in ("acknowledge", "observe", "capture", "stop", "resume"):
        command = commands.add_parser(action)
        command.add_argument("--run-id", required=True)
        command.add_argument("--key", required=True)
        command.add_argument("--expected-storage", required=True)
        if action == "acknowledge":
            command.add_argument("--provider-run-id", required=True)
    arguments = parser.parse_args(argv)
    try:
        settings = RuntimeConfig.from_environment()
        # Reject a mistaken target before opening/migrating a workspace.
        binding = storage_binding(Path(settings.directory) / "workspace.sqlite")
        if (
            arguments.command not in ("status", "inspect")
            and arguments.expected_storage != binding
        ):
            raise Conflict(
                "operator storage binding differs from the configured workspace"
            )
        workspace = Workspace(Path(settings.directory))
        operator = WeatherOperator(workspace)
        if arguments.command == "status":
            reply = ExecutionControl(workspace).status()
        elif arguments.command == "inspect":
            reply = operator.inspect(arguments.run_id)
        else:
            actor = Actor("team", "local-operator:" + str(os.getuid()))
            if arguments.command == "resume":
                weather = settings.weather_service(workspace)
                reply = operator.resume(
                    actor,
                    arguments.run_id,
                    None if weather is None else weather.kernel,
                    key=arguments.key,
                )
            else:
                reply = operator.admit(
                    actor,
                    arguments.run_id,
                    arguments.command,
                    provider_run_id=getattr(arguments, "provider_run_id", None),
                    key=arguments.key,
                )
        print(encode(reply).decode())
        return 0
    except PlanningError as error:
        print(encode({"schema_version": 1, "error": {"code": error.code}}).decode())
        return 1
    except Exception:
        LOG.exception("private weather operation failed")
        print(
            encode({"schema_version": 1, "error": {"code": "operator_failed"}}).decode()
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
