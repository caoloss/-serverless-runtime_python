import http.client
import http.server
import json
import logging
import sys
import threading
import time
import urllib.request
from typing import Any

from serverless_aws_lambda_otel_extension.external.context import extension_context
from serverless_aws_lambda_otel_extension.external.threading import (
    extension_registered_event,
    log_registered_event,
    log_server_active_event,
    otel_server_active_event,
)
from serverless_aws_lambda_otel_extension.shared.constants import (
    HTTP_CONTENT_TYPE_APPLICATION_JSON,
    HTTP_CONTENT_TYPE_HEADER,
    HTTP_METHOD_POST,
    HTTP_METHOD_PUT,
    LAMBDA_EXTENSION_IDENTIFIER_HEADER,
    LAMBDA_EXTENSION_NAME_HEADER,
    SERVERLESS_AWS_LAMBDA_OTEL_EXTENSION_NAME,
)
from serverless_aws_lambda_otel_extension.shared.settings import settings
from serverless_aws_lambda_otel_extension.shared.utilities import (
    build_extensions_api_next_url,
    build_extensions_api_register_url,
    build_log_server_url,
    build_logs_api_register_url,
)

logger = logging.getLogger(__name__)


class OtelHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_POST(self) -> None:

        http_request: urllib.request.Request
        http_response: http.client.HTTPResponse

        try:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        except Exception:
            logger.exception("Failed to parse payload")
            payload = {}

        logger.debug("payload:%s", payload)

        record_type = payload.get("recordType")

        if record_type == "eventData":

            http_request = urllib.request.Request(
                "https://webhook.site/74ac6791-fc37-4f4a-92b0-34e794bd0bf7/eventData",
                method=HTTP_METHOD_POST,
                headers={
                    HTTP_CONTENT_TYPE_HEADER: HTTP_CONTENT_TYPE_APPLICATION_JSON,
                    LAMBDA_EXTENSION_IDENTIFIER_HEADER: SERVERLESS_AWS_LAMBDA_OTEL_EXTENSION_NAME,
                    LAMBDA_EXTENSION_NAME_HEADER: SERVERLESS_AWS_LAMBDA_OTEL_EXTENSION_NAME,
                },
                data=json.dumps(
                    {
                        "context": {
                            "extension_id": extension_context.extension_id,
                            "execution_id": extension_context.execution_id,
                        },
                        "payload": payload,
                    }
                ).encode("utf-8"),
            )
            http_response = urllib.request.urlopen(http_request)
            http_response.read()

        elif record_type == "telemetryData":

            http_request = urllib.request.Request(
                "https://webhook.site/74ac6791-fc37-4f4a-92b0-34e794bd0bf7/telemetryData",
                method=HTTP_METHOD_POST,
                headers={
                    HTTP_CONTENT_TYPE_HEADER: HTTP_CONTENT_TYPE_APPLICATION_JSON,
                    LAMBDA_EXTENSION_IDENTIFIER_HEADER: SERVERLESS_AWS_LAMBDA_OTEL_EXTENSION_NAME,
                    LAMBDA_EXTENSION_NAME_HEADER: SERVERLESS_AWS_LAMBDA_OTEL_EXTENSION_NAME,
                },
                data=json.dumps(
                    {
                        "context": {
                            "extension_id": extension_context.extension_id,
                            "execution_id": extension_context.execution_id,
                        },
                        "payload": payload,
                    }
                ).encode("utf-8"),
            )
            http_response = urllib.request.urlopen(http_request)
            http_response.read()

        self.send_response(200)
        self.end_headers()


class LogHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_POST(self) -> None:
        self.send_response(200)
        self.end_headers()

    # Documentation is unclear on if certian runtimes will prefer PUT over POST.
    do_PUT = do_POST


class OtelThreadingHTTPServer(http.server.ThreadingHTTPServer):

    request_queue_size: int = 20

    def service_actions(self) -> None:
        return super().service_actions()

    def server_activate(self) -> None:
        otel_server_active_event.set()
        return super().server_activate()


class LogThreadingHTTPServer(http.server.ThreadingHTTPServer):

    request_queue_size: int = 20

    def service_actions(self) -> None:
        return super().service_actions()

    def server_activate(self) -> None:
        log_server_active_event.set()
        return super().server_activate()


def extensions_api_register_once():

    # We want to wait for this to be up before we register and attempt to process an event.
    otel_server_active_event.wait()

    http_request: urllib.request.Request
    http_response: http.client.HTTPResponse

    http_request = urllib.request.Request(
        build_extensions_api_register_url(),
        method=HTTP_METHOD_POST,
        headers={
            HTTP_CONTENT_TYPE_HEADER: HTTP_CONTENT_TYPE_APPLICATION_JSON,
            LAMBDA_EXTENSION_NAME_HEADER: SERVERLESS_AWS_LAMBDA_OTEL_EXTENSION_NAME,
        },
        data=bytes(json.dumps({"events": ["INVOKE", "SHUTDOWN"]}), "utf-8"),
    )

    http_response = urllib.request.urlopen(http_request)
    http_response.read()

    extension_context.set_extension_id(http_response.getheader("Lambda-Extension-Identifier"))

    extension_registered_event.set()


def logs_api_register_once():

    log_server_active_event.wait()

    http_request: urllib.request.Request
    http_response: http.client.HTTPResponse

    http_request = urllib.request.Request(
        build_logs_api_register_url(),
        method=HTTP_METHOD_PUT,
        headers={
            HTTP_CONTENT_TYPE_HEADER: HTTP_CONTENT_TYPE_APPLICATION_JSON,
            LAMBDA_EXTENSION_IDENTIFIER_HEADER: extension_context.extension_id,
        },
        data=bytes(
            json.dumps(
                {
                    "schemaVersion": "2021-03-18",
                    "types": ["platform", "extension", "function"],
                    "buffering": {
                        "maxItems": 1000,
                        "maxBytes": 262144,
                        "timeoutMs": 100,
                    },
                    "destination": {
                        "protocol": "HTTP",
                        "URI": build_log_server_url(),
                    },
                }
            ),
            "utf-8",
        ),
    )

    logger.debug("logs_api_register_once:request:%s", http_request)

    http_response = urllib.request.urlopen(http_request)
    http_response.read()

    log_registered_event.set()


def extensions_api_next_loop():

    extension_registered_event.wait()
    log_registered_event.wait()

    http_request: urllib.request.Request
    http_response: http.client.HTTPResponse

    while True:
        http_request = urllib.request.Request(
            build_extensions_api_next_url(),
            headers={
                LAMBDA_EXTENSION_IDENTIFIER_HEADER: extension_context.extension_id,
            },
        )

        http_response = urllib.request.urlopen(http_request, timeout=3600)
        response_body = http_response.read()

        payload = json.loads(response_body)

        if payload.get("eventType") == "SHUTDOWN":
            sys.exit(0)


def otel_http_server_serve(addr, port):

    with OtelThreadingHTTPServer((addr, port), OtelHTTPRequestHandler) as server:
        server.serve_forever(poll_interval=None)


def log_http_server_serve(addr, port):

    extension_registered_event.wait()

    with LogThreadingHTTPServer((addr, port), LogHTTPRequestHandler) as server:
        server.serve_forever(poll_interval=None)


def start():

    serverless_runtime_server_thread = threading.Thread(
        target=otel_http_server_serve,
        args=(settings.otel_server_host, settings.otel_server_port),
        daemon=True,
    )

    serverless_runtime_server_thread.start()

    serverless_runtime_log_server_thread = threading.Thread(
        target=log_http_server_serve,
        args=(settings.log_server_host, settings.log_server_port),
        daemon=True,
    )

    serverless_runtime_log_server_thread.start()

    extension_client_register_thread = threading.Thread(target=extensions_api_register_once, daemon=True)
    extension_client_register_thread.start()

    log_register_thread = threading.Thread(target=logs_api_register_once, daemon=True)
    log_register_thread.start()

    extension_client_next_loop_thread = threading.Thread(target=extensions_api_next_loop, daemon=True)
    extension_client_next_loop_thread.start()

    try:
        while True:
            # add more here to check for shutdown
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    sys.exit(0)


if __name__ == "__main__":
    start()


# {
#     "eventType": "INVOKE",
#     "deadlineMs": 1654468766618,
#     "requestId": "dbdb0d38-24e5-45eb-ad4f-3234faaa30d5",
#     "invokedFunctionArn": "arn:aws:lambda:us-east-1:377024778620:function:runtime-python-example-dev-hello",
#     "tracing": {
#         "type": "X-Amzn-Trace-Id",
#         "value": "Root=1-629d3097-1edcadf06b4c097a50faa7a1;Parent=2a68d66d2a726db8;Sampled=0",
#     },
# }

# {
#     "eventType": "SHUTDOWN",
#     "deadlineMs": 1654469121614,
#     "shutdownReason": "spindown",
# }

# {
#     "eventType": "SHUTDOWN",
#     "deadlineMs": 1654470414327,
#     "shutdownReason": "timeout",
# }

# SPINDOWN, TIMEOUT, FAILURE

# {
#     "name": "handler.hello",
#     "context": {
#         "trace_id": "0xb33bfbd55d86873c64136e22832f82d6",
#         "span_id": "0x773584354928d957",
#         "trace_state": "[]",
#     },
#     "kind": "SpanKind.SERVER",
#     "parent_id": null,
#     "start_time": "2022-06-05T22:39:20.622887Z",
#     "end_time": "2022-06-05T22:39:20.625299Z",
#     "status": {"status_code": "UNSET"},
#     "attributes": {
#         "faas.id": "arn:aws:lambda:us-east-1:377024778620:function:runtime-python-example-dev-hello",
#         "faas.execution": "dbdb0d38-24e5-45eb-ad4f-3234faaa30d5",
#     },
#     "events": [],
#     "links": [],
#     "resource": {"service.name": "your-service-name"},
# }

# [
#     {
#         "time": "2022-06-05T23:53:22.289Z",
#         "type": "platform.start",
#         "record": {"requestId": "00bbcc13-f812-41d1-a9ef-8486fbc0b99c", "version": "$LATEST"},
#     },
#     {
#         "time": "2022-06-05T23:53:22.289Z",
#         "type": "platform.extension",
#         "record": {
#             "name": "serverless_aws_lambda_otel_extension.py",
#             "state": "Ready",
#             "events": ["INVOKE", "SHUTDOWN"],
#         },
#     },
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": "{\n"},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"name": "handler.hello",\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"context": {\n'},
#     {
#         "time": "2022-06-05T23:53:22.296Z",
#         "type": "function",
#         "record": '"trace_id": "0x77986fa86dac783f1cf430b7b7cc19dd",\n',
#     },
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"span_id": "0xe03ba74521ddce35",\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"trace_state": "[]"\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": "},\n"},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"kind": "SpanKind.SERVER",\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"parent_id": null,\n'},
#     {
#         "time": "2022-06-05T23:53:22.296Z",
#         "type": "function",
#         "record": '"start_time": "2022-06-05T23:53:22.293726Z",\n',
#     },
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"end_time": "2022-06-05...
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"status": {\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"status_code": "UNSET"\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": "},\n"},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"attributes": {\n'},
#     {
#         "time": "2022-06-05T23:53:22.296Z",
#         "type": "function",
#         "record": '"faas.id": "arn:aws:lambda:us-east-1:377024778620:function:runtime-python-example-dev-hello",\n',
#     },
#     {
#         "time": "2022-06-05T23:53:22.296Z",
#         "type": "function",
#         "record": '"faas.execution": "00bbcc13-f812-41d1-a9ef-8486fbc0b99c"\n',
#     },
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": "},\n"},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"events": [],\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"links": [],\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"resource": {\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": '"service.name": "your-service-name"\n'},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": "}\n"},
#     {"time": "2022-06-05T23:53:22.296Z", "type": "function", "record": "}\n"},
#     {
#         "time": "2022-06-05T23:53:22.309Z",
#         "type": "platform.runtimeDone",
#         "record": {"requestId": "00bbcc13-f812-41d1-a9ef-8486fbc0b99c", "status": "success"},
#     },
# ]
