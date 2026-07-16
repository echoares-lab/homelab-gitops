#!/usr/bin/env python3
"""Independent k3s Watchdog receiver and SES notifier."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import argparse
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import smtplib
import ssl
import threading
import time
from typing import Any


DEADLINE_SECONDS = 600
REPEAT_SECONDS = 3600


@dataclass(frozen=True)
class State:
    armed: bool = False
    last_heartbeat: float = 0.0
    alert_active: bool = False
    recovery_pending: bool = False
    last_notification: float = 0.0
    accepted_heartbeats: int = 0
    rejected_heartbeats: int = 0
    ses_successes: int = 0
    ses_failures: int = 0


def valid_watchdog_payload(payload: dict[str, Any]) -> bool:
    if payload.get("status") != "firing":
        return False
    return any(
        alert.get("status", "firing") == "firing"
        and alert.get("labels", {}).get("alertname") == "Watchdog"
        for alert in payload.get("alerts", [])
    )


def record_heartbeat(state: State, now: float) -> State:
    return replace(
        state,
        last_heartbeat=now,
        recovery_pending=state.alert_active,
        accepted_heartbeats=state.accepted_heartbeats + 1,
    )


def transition(state: State, now: float) -> tuple[State, str | None]:
    if not state.armed:
        return state, None
    if state.recovery_pending:
        return state, "recovery"
    if now - state.last_heartbeat < DEADLINE_SECONDS:
        return state, None
    if not state.alert_active or now - state.last_notification >= REPEAT_SECONDS:
        return state, "critical"
    return state, None


def mark_sent(state: State, event: str, now: float) -> State:
    if event == "critical":
        return replace(
            state,
            alert_active=True,
            last_notification=now,
            ses_successes=state.ses_successes + 1,
        )
    if event == "recovery":
        return replace(
            state,
            alert_active=False,
            recovery_pending=False,
            last_notification=now,
            ses_successes=state.ses_successes + 1,
        )
    raise ValueError(f"unknown event: {event}")


def render_metrics(state: State, now: float) -> str:
    age = max(0, int(now - state.last_heartbeat))
    lines = [
        "# HELP k3s_deadman_heartbeat_age_seconds Age of the last valid Watchdog heartbeat.",
        "# TYPE k3s_deadman_heartbeat_age_seconds gauge",
        f"k3s_deadman_heartbeat_age_seconds {age}",
        f"k3s_deadman_armed {int(state.armed)}",
        f"k3s_deadman_alert_active {int(state.alert_active)}",
        f'k3s_deadman_heartbeats_total{{result="accepted"}} {state.accepted_heartbeats}',
        f'k3s_deadman_heartbeats_total{{result="rejected"}} {state.rejected_heartbeats}',
        f'k3s_deadman_ses_total{{result="success"}} {state.ses_successes}',
        f'k3s_deadman_ses_total{{result="failure"}} {state.ses_failures}',
    ]
    return "\n".join(lines) + "\n"


def load_state(path: Path) -> State:
    try:
        return State(**json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return State()


def save_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(state), sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


class StateManager:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.state = load_state(path)

    def update(self, operation):
        with self.lock:
            self.state = operation(self.state)
            save_state(self.path, self.state)
            return self.state

    def snapshot(self) -> State:
        with self.lock:
            return self.state


def credential(name: str) -> str:
    directory = Path(os.environ.get("CREDENTIALS_DIRECTORY", "/run/credentials"))
    return (directory / name).read_text(encoding="utf-8").strip()


def send_ses(event: str, state: State) -> None:
    sender = "alerts@mail.plexplease.com"
    recipient = "matthewgraypdx@gmail.com"
    message = EmailMessage()
    label = "CRITICAL" if event == "critical" else "RECOVERY"
    message["Subject"] = f"[{label}][EXTERNAL DEADMAN] k3s-01 monitoring heartbeat"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"event={event}\nlast_heartbeat_epoch={state.last_heartbeat:.0f}\n"
        f"alert_active={state.alert_active}\n"
    )
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(
        "email-smtp.us-east-1.amazonaws.com", 465, timeout=20, context=context
    ) as client:
        client.login(credential("ses_username"), credential("ses_password"))
        client.send_message(message)


def heartbeat_handler(manager: StateManager):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/heartbeat":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(min(length, 1_048_576)))
            except (ValueError, json.JSONDecodeError):
                payload = {}
            if not valid_watchdog_payload(payload):
                manager.update(
                    lambda state: replace(
                        state, rejected_heartbeats=state.rejected_heartbeats + 1
                    )
                )
                self.send_error(400, "firing Watchdog alert required")
                return
            manager.update(lambda state: record_heartbeat(state, time.time()))
            self.send_response(204)
            self.end_headers()

        def log_message(self, format, *args):
            return

    return Handler


def status_handler(manager: StateManager):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                body = b"ok\n"
                content_type = "text/plain"
            elif self.path == "/metrics":
                body = render_metrics(manager.snapshot(), time.time()).encode()
                content_type = "text/plain; version=0.0.4"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return Handler


def notification_loop(manager: StateManager) -> None:
    while True:
        state, event = transition(manager.snapshot(), time.time())
        if event:
            try:
                send_ses(event, state)
                manager.update(lambda current: mark_sent(current, event, time.time()))
            except Exception:
                manager.update(
                    lambda current: replace(
                        current, ses_failures=current.ses_failures + 1
                    )
                )
        time.sleep(60)


def serve(state_path: Path) -> None:
    manager = StateManager(state_path)
    heartbeat = ThreadingHTTPServer(("0.0.0.0", 9443), heartbeat_handler(manager))
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=str(Path(os.environ["CREDENTIALS_DIRECTORY"]) / "ca_crt"))
    context.load_cert_chain(
        certfile=str(Path(os.environ["CREDENTIALS_DIRECTORY"]) / "server_crt"),
        keyfile=str(Path(os.environ["CREDENTIALS_DIRECTORY"]) / "server_key"),
    )
    heartbeat.socket = context.wrap_socket(heartbeat.socket, server_side=True)
    metrics = ThreadingHTTPServer(("0.0.0.0", 9101), status_handler(manager))
    threading.Thread(target=heartbeat.serve_forever, daemon=True).start()
    threading.Thread(target=metrics.serve_forever, daemon=True).start()
    notification_loop(manager)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("command", nargs="?", choices=("serve", "arm", "disarm", "status", "test-email"), default="serve")
    args = parser.parse_args()
    manager = StateManager(args.state)
    if args.command == "serve":
        serve(args.state)
    elif args.command in {"arm", "disarm"}:
        manager.update(lambda state: replace(state, armed=args.command == "arm", last_heartbeat=time.time()))
    elif args.command == "status":
        print(json.dumps(asdict(manager.snapshot()), sort_keys=True))
    elif args.command == "test-email":
        send_ses("recovery", manager.snapshot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
