from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from resend_email_skill.attachments import normalize_attachment, normalize_attachment_list, write_attachment
from resend_email_skill.client import ResendClient
from resend_email_skill.config import doctor_info, load_settings
from resend_email_skill.errors import ResendEmailSkillError, ValidationError
from resend_email_skill.markdown import export_markdown
from resend_email_skill.receiver import normalize_email, normalize_list_response, poll_for_subject
from resend_email_skill.sender import build_send_payload, summarize_payload


def emit(payload: dict[str, Any], *, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def emit_error(exc: ResendEmailSkillError) -> None:
    payload = {"error": exc.message, "error_type": exc.error_type, "status_code": exc.status_code, "response": exc.response}
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resend-email")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_format(target: argparse.ArgumentParser) -> None:
        target.add_argument("--format", choices=["json", "text"], default=argparse.SUPPRESS)

    doctor = subparsers.add_parser("doctor")
    add_format(doctor)
    doctor_sub = doctor.add_subparsers(dest="doctor_command", required=True)
    doctor_config = doctor_sub.add_parser("config")
    add_format(doctor_config)

    send = subparsers.add_parser("send")
    add_format(send)
    send.add_argument("--from", dest="from_email")
    send.add_argument("--to", action="append", required=True)
    send.add_argument("--cc", action="append")
    send.add_argument("--bcc", action="append")
    send.add_argument("--reply-to", action="append", dest="reply_to")
    send.add_argument("--subject", required=True)
    send.add_argument("--html")
    send.add_argument("--text")
    send.add_argument("--body-file")
    send.add_argument("--body-format", choices=["markdown", "md", "html", "text", "txt", "plain"])
    send.add_argument("--attach", action="append")
    send.add_argument("--header", action="append", help='Repeatable custom header in "Name: Value" format.')
    send.add_argument("--idempotency-key")
    send.add_argument("--max-attempts", type=int, choices=range(1, 6), default=1)
    send.add_argument("--dry-run", action="store_true")
    send.add_argument("--confirm-send", action="store_true", help="Required for real sends. Omit only when using --dry-run.")

    received = subparsers.add_parser("received")
    add_format(received)
    received_sub = received.add_subparsers(dest="received_command", required=True)
    received_list = received_sub.add_parser("list")
    add_format(received_list)
    received_list.add_argument("--limit", type=int, default=20)
    received_list.add_argument("--after")
    received_list.add_argument("--before")

    received_get = received_sub.add_parser("get")
    add_format(received_get)
    received_get.add_argument("email_id")

    export = received_sub.add_parser("export-md")
    add_format(export)
    export.add_argument("email_id")
    export.add_argument("--output-dir", default="data/received/markdown")

    export_all = received_sub.add_parser("export-all-md")
    add_format(export_all)
    export_all.add_argument("--output-dir", default="data/received/markdown")
    export_all.add_argument("--limit", type=int, default=20)
    export_all.add_argument("--after")
    export_all.add_argument("--before")

    poll = received_sub.add_parser("poll")
    add_format(poll)
    poll.add_argument("--subject-prefix", required=True)
    poll.add_argument("--timeout", type=int, default=60)
    poll.add_argument("--interval", type=float, default=2.0)
    poll.add_argument("--limit", type=int, default=20)

    attachments = received_sub.add_parser("attachments")
    add_format(attachments)
    attachment_sub = attachments.add_subparsers(dest="attachment_command", required=True)
    attachment_list = attachment_sub.add_parser("list")
    add_format(attachment_list)
    attachment_list.add_argument("email_id")
    attachment_list.add_argument("--limit", type=int, default=100)
    attachment_list.add_argument("--after")
    attachment_list.add_argument("--before")

    attachment_download = attachment_sub.add_parser("download")
    add_format(attachment_download)
    attachment_download.add_argument("email_id")
    attachment_download.add_argument("attachment_id")
    attachment_download.add_argument("--output-dir", default="data/received/attachments")

    suppressions = subparsers.add_parser("suppressions")
    add_format(suppressions)
    suppression_sub = suppressions.add_subparsers(dest="suppression_command", required=True)
    suppression_list = suppression_sub.add_parser("list")
    add_format(suppression_list)
    suppression_list.add_argument("--limit", type=int, choices=range(1, 101), default=20)
    suppression_list.add_argument("--after")
    suppression_list.add_argument("--before")
    suppression_list.add_argument("--origin", choices=["bounce", "complaint", "manual"])
    suppression_list.add_argument("--all", action="store_true", dest="list_all")

    suppression_get = suppression_sub.add_parser("get")
    add_format(suppression_get)
    suppression_get.add_argument("suppression")

    suppression_add = suppression_sub.add_parser("add")
    add_format(suppression_add)
    suppression_add.add_argument("email")
    suppression_add.add_argument("--dry-run", action="store_true")
    suppression_add.add_argument("--confirm-add", action="store_true")

    suppression_remove = suppression_sub.add_parser("remove")
    add_format(suppression_remove)
    suppression_remove.add_argument("suppression")
    suppression_remove.add_argument("--dry-run", action="store_true")
    suppression_remove.add_argument("--confirm-remove", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = load_settings()
    client = ResendClient(settings)
    if args.command == "doctor":
        return {"status": "ok", "config": doctor_info(settings)}
    if args.command == "send":
        payload = build_send_payload(
            settings=settings,
            from_email=args.from_email,
            to=args.to,
            subject=args.subject,
            html=args.html,
            text=args.text,
            body_file=args.body_file,
            body_format=args.body_format,
            cc=args.cc,
            bcc=args.bcc,
            reply_to=args.reply_to,
            attach=args.attach,
            headers=args.header,
        )
        if args.max_attempts > 1 and not args.idempotency_key:
            raise ValidationError("Retrying a send requires --idempotency-key.")
        if args.dry_run:
            return {"status": "dry_run", "sent": False, "max_attempts": args.max_attempts, "payload": summarize_payload(payload)}
        if not args.confirm_send:
            raise ResendEmailSkillError("Real sends require --confirm-send. Run with --dry-run first.", error_type="send_not_confirmed")
        response = client.send_email(payload, idempotency_key=args.idempotency_key, max_attempts=args.max_attempts)
        return {"status": "sent", "sent": True, "response": response}
    if args.command == "received":
        if args.received_command == "list":
            return normalize_list_response(client.list_received(limit=args.limit, after=args.after, before=args.before))
        if args.received_command == "get":
            return normalize_email(client.get_received(args.email_id))
        if args.received_command == "export-md":
            email = client.get_received(args.email_id)
            path = export_markdown(email, Path(args.output_dir))
            return {"status": "exported", "path": str(path), "email": normalize_email(email)}
        if args.received_command == "export-all-md":
            listed = normalize_list_response(client.list_received(limit=args.limit, after=args.after, before=args.before))
            paths = []
            for item in listed["data"]:
                email_id = item.get("id")
                if not email_id:
                    continue
                email = client.get_received(str(email_id))
                paths.append(str(export_markdown(email, Path(args.output_dir))))
            return {"status": "exported", "count": len(paths), "paths": paths, "has_more": listed["has_more"]}
        if args.received_command == "poll":
            email = poll_for_subject(client, args.subject_prefix, args.timeout, interval=args.interval, limit=args.limit)
            return {"status": "found", "email": email}
        if args.received_command == "attachments":
            if args.attachment_command == "list":
                return normalize_attachment_list(
                    client.list_received_attachments(args.email_id, limit=args.limit, after=args.after, before=args.before)
                )
            if args.attachment_command == "download":
                attachment = normalize_attachment(client.get_received_attachment(args.email_id, args.attachment_id))
                url = attachment.get("download_url")
                if not url:
                    raise ResendEmailSkillError("Attachment response did not include download_url", error_type="missing_download_url")
                content = client.download_url(str(url))
                path = write_attachment(content, Path(args.output_dir), attachment.get("filename"), str(args.attachment_id))
                return {"status": "downloaded", "path": str(path), "attachment": attachment, "size": len(content)}
    if args.command == "suppressions":
        if args.suppression_command == "list":
            if args.list_all and args.before:
                raise ValidationError("--all cannot be combined with --before; use --after to resume forward pagination.")
            response = client.list_suppressions(
                limit=args.limit,
                after=args.after,
                before=args.before,
                origin=args.origin,
            )
            if not args.list_all:
                return response
            data = list(response.get("data", []))
            while response.get("has_more"):
                cursor = data[-1].get("id") if data else None
                if not cursor:
                    raise ResendEmailSkillError(
                        "Suppression pagination response has_more=true but no final id cursor.",
                        error_type="invalid_api_response",
                    )
                response = client.list_suppressions(limit=args.limit, after=str(cursor), origin=args.origin)
                data.extend(response.get("data", []))
            return {"object": "list", "has_more": False, "data": data, "count": len(data)}
        if args.suppression_command == "get":
            return client.get_suppression(args.suppression)
        if args.suppression_command == "add":
            if args.dry_run:
                return {"status": "dry_run", "changed": False, "action": "add", "email": args.email}
            if not args.confirm_add:
                raise ResendEmailSkillError(
                    "Adding a suppression requires --confirm-add. Run with --dry-run first.",
                    error_type="suppression_change_not_confirmed",
                )
            return {"status": "added", "changed": True, "response": client.add_suppression(args.email)}
        if args.suppression_command == "remove":
            if args.dry_run:
                return {"status": "dry_run", "changed": False, "action": "remove", "suppression": args.suppression}
            if not args.confirm_remove:
                raise ResendEmailSkillError(
                    "Removing a suppression requires --confirm-remove. Run with --dry-run first.",
                    error_type="suppression_change_not_confirmed",
                )
            return {"status": "removed", "changed": True, "response": client.remove_suppression(args.suppression)}
    raise ResendEmailSkillError("Unsupported command", error_type="unsupported_command")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        emit(run(args), fmt=args.format)
        return 0
    except ResendEmailSkillError as exc:
        emit_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
