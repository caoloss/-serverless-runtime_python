import http.client
import json
import os
import urllib.request
from functools import lru_cache
from importlib import import_module
from typing import Any, Callable, Dict

from opentelemetry import trace
from opentelemetry.instrumentation.aws_lambda import AwsLambdaInstrumentor
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider

from serverless_aws_lambda_otel_extension.internal.span.exporter import in_memory_span_exporter
from serverless_aws_lambda_otel_extension.internal.span.processor import serverless_span_processor
from serverless_aws_lambda_otel_extension.shared.constants import (
    HTTP_CONTENT_TYPE_APPLICATION_JSON,
    HTTP_CONTENT_TYPE_HEADER,
    HTTP_METHOD_POST,
)
from serverless_aws_lambda_otel_extension.shared.utilities import build_otel_server_url


@lru_cache
def configure_environment() -> None:

    os.environ.setdefault("OTEL_INSTRUMENTATION_AWS_LAMBDA_FLUSH_TIMEOUT", "100")


@lru_cache
def configure_tracer() -> None:

    resource = Resource(attributes={SERVICE_NAME: "your-service-name"})

    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(serverless_span_processor)

    trace.set_tracer_provider(trace_provider)


@lru_cache
def get_actual_handler() -> Callable:

    handler_module_name, handler_function_name = os.environ["ORIG_HANDLER"].rsplit(".", 1)
    handler_module = import_module(handler_module_name)

    return getattr(handler_module, handler_function_name)


@lru_cache
def do_instrumentation() -> None:

    AwsLambdaInstrumentor().instrument()
    BotocoreInstrumentor().instrument()
    RequestsInstrumentor().instrument()


def auto_instrumenting_handler(event: Dict, context: Any) -> Dict:

    configure_environment()
    configure_tracer()
    do_instrumentation()

    actual_handler = get_actual_handler()

    # ConsoleSpanExporter().export(spans=in_memory_span_exporter.get_finished_spans())

    in_memory_span_exporter.clear()

    handler_event_data = {
        "recordType": "eventData",
    }

    http_request: urllib.request.Request
    http_response: http.client.HTTPResponse

    http_request = urllib.request.Request(
        build_otel_server_url(),
        method=HTTP_METHOD_POST,
        headers={
            HTTP_CONTENT_TYPE_HEADER: HTTP_CONTENT_TYPE_APPLICATION_JSON,
        },
        data=bytes(json.dumps(handler_event_data), "utf-8"),
    )

    http_response = urllib.request.urlopen(http_request)
    http_response.read()

    actual_response = actual_handler(event, context)

    handler_telemetry_data = {
        "recordType": "telemetryData",
    }

    http_request = urllib.request.Request(
        build_otel_server_url(),
        method=HTTP_METHOD_POST,
        headers={
            HTTP_CONTENT_TYPE_HEADER: HTTP_CONTENT_TYPE_APPLICATION_JSON,
        },
        data=bytes(json.dumps(handler_telemetry_data), "utf-8"),
    )

    http_response = urllib.request.urlopen(http_request)
    http_response.read()

    # # This is handled after the fact so we can capture the current span id
    # handler_request_event = {
    #     "recordType": "eventData",
    #     "record": {
    #         "eventData": {
    #             "1dd2364c-227c-4a7b-9312-2bea72b22303": {
    #                 "service.name": "unknown_service:/var/lang/bin/node",
    #                 "telemetry.sdk.language": "nodejs",
    #                 "telemetry.sdk.name": "opentelemetry",
    #                 "telemetry.sdk.version": "1.2.0",
    #                 "cloud.provider": "aws",
    #                 "cloud.platform": "aws_lambda",
    #                 "cloud.region": "us-east-1",
    #                 "faas.name": "aws-node-http-api-project-shane-dev-hello",
    #                 "faas.version": "$LATEST",
    #                 "sls_service_name": "aws-node-http-api-project",
    #                 "sls_stage": "shane-dev",
    #                 "sls_org_id": "5d0a5542-366d-4d23-8626-cd4fa5532581",
    #                 "process.pid": 16,
    #                 "process.executable.name": "/var/lang/bin/node",
    #                 "process.command": "/var/runtime/index.js",
    #                 "process.command_line": "/var/lang/bin/node /var/runtime/index.js",
    #                 "process.runtime.version": "14.19.1",
    #                 "process.runtime.name": "nodejs",
    #                 "process.runtime.description": "Node.js",
    #                 "computeCustomArn": "arn:aws:lambda:us-east-1:377024778620:function:aws-n",
    #                 "functionName": "aws-node-http-api-project-shane-dev-hello",
    #                 "computeRegion": "us-east-1",
    #                 "computeRuntime": "aws.lambda.nodejs.14.19.1",
    #                 "computeCustomFunctionVersion": "$LATEST",
    #                 "computeMemorySize": "1024",
    #                 "eventCustomXTraceId": "Root=1-628ad20c-4483a2ac0d360ca91e69b91f;Parent=3a2a9a9f6;Sampled=0",
    #                 "computeCustomLogGroupName": "/aws/lambda/aws-node-http-api-project-shane-dev-hello",
    #                 "computeCustomLogStreamName": "2022/05/23/[$LATEST]1ea0137e2e0842c892344703ead98587",
    #                 "computeCustomEnvArch": "x64",
    #                 "eventType": "aws.apigatewayv2.http",
    #                 "eventCustomRequestId": "1dd2364c-227c-4a7b-9312-2bea72b22303",
    #                 "computeIsColdStart": True,
    #                 "eventCustomDomain": "0c47e3drf5.execute-api.us-east-1.amazonaws.com",
    #                 "eventCustomRequestTimeEpoch": 1653264908691,
    #                 "eventCustomApiId": "0c47e3drf5",
    #                 "eventSource": "aws.apigateway",
    #                 "eventCustomAccountId": "377024778620",
    #                 "httpPath": "/",
    #                 "rawHttpPath": "/",
    #                 "eventCustomHttpMethod": "GET",
    #             }
    #         },
    #         "span": {"traceId": "0eb47c6f7e03ffa6db235957bbc6023d", "spanId": "9a8f4befa3e1bf37"},
    #         "requestEventPayload": event,
    #     },
    # }

    # handler_response_telemetry = {}

    return actual_response
