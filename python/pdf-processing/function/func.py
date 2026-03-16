"""HTTP entrypoint for the PDF processing function.

This is a thin ASGI routing layer. All PDF logic lives in :mod:`pdf_ops`.
"""

import json
import logging
from urllib.parse import parse_qs

from .pdf_ops import (
    InvalidPDFError,
    ProcessingError,
    extract_text,
    get_metadata,
    merge_pdfs,
    split_pages,
)

MAX_BODY = 10 * 1024 * 1024  # 10 MB


def new():
    return Function()


async def send_response(
    send, body: bytes | str, status: int = 200,
    content_type: bytes = b"application/json",
) -> None:
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", content_type]],
    })
    await send({
        "type": "http.response.body",
        "body": body if isinstance(body, bytes) else body.encode(),
    })


class Function:

    async def handle(self, scope, receive, send) -> None:
        if scope["method"] == "GET":
            await send_response(
                send,
                json.dumps({"status": "ok", "ops": ["extract-text", "metadata", "split", "merge"]}),
            )
            return

        # --- read body with size guard ---
        body = b""
        more_body = True
        while more_body:
            msg = await receive()
            body += msg.get("body", b"")
            if len(body) > MAX_BODY:
                return await send_response(
                    send, json.dumps({"error": "body exceeds 10 MB limit"}), status=413,
                )
            more_body = msg.get("more_body", False)

        if not body:
            return await send_response(
                send, json.dumps({"error": "empty body"}), status=400,
            )

        # --- dispatch operation ---
        qs = parse_qs(scope.get("query_string", b"").decode())
        op = qs.get("op", [""])[0]

        try:
            if op == "extract-text":
                text = extract_text(body)
                await send_response(send, json.dumps({"text": text}))

            elif op == "metadata":
                meta = get_metadata(body)
                await send_response(send, json.dumps(meta))

            elif op == "split":
                zip_bytes = split_pages(body)
                await send_response(send, zip_bytes, content_type=b"application/zip")

            elif op == "merge":
                pdf_bytes = merge_pdfs(body)
                await send_response(send, pdf_bytes, content_type=b"application/pdf")

            else:
                await send_response(
                    send,
                    json.dumps({"error": "use ?op=extract-text|metadata|split|merge"}),
                    status=400,
                )

        except InvalidPDFError as exc:
            await send_response(
                send, json.dumps({"error": str(exc)}), status=422,
            )
        except ProcessingError:
            logging.exception("Error processing PDF")
            await send_response(
                send,
                json.dumps({"error": "failed to process PDF"}),
                status=422,
            )
        except Exception:
            logging.exception("Unexpected error in PDF handler")
            await send_response(
                send,
                json.dumps({"error": "internal server error"}),
                status=500,
            )

    def start(self, cfg) -> None:
        logging.info("Function starting")

    def stop(self) -> None:
        logging.info("Function stopping")

    def alive(self) -> tuple[bool, str]:
        return True, "Alive"

    def ready(self) -> tuple[bool, str]:
        return True, "Ready"
