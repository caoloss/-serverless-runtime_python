import os
from typing import Dict

from serverless_aws_lambda_otel_extension.shared.constants import (
    EXTENSIONS_API_EVENT_NEXT_PATH,
    EXTENSIONS_API_REGISTER_PATH,
    LOGS_API_PATH,
    OTEL_RESOURCE_ATTRIBUTES_ENV_VAR,
    SLS_OTEL_RESOURCE_ATTRIBUTES_ENV_VAR,
    SLS_OTEL_RESOURCE_ATTRIBUTES_ORG_ID_VAR,
    SLS_OTEL_RESOURCE_ATTRIBUTES_SERVICE_NAME_VAR,
    SLS_OTEL_RESOURCE_ATTRIBUTES_STAGE_VAR,
)
from serverless_aws_lambda_otel_extension.shared.defaults import (
    DEFAULT_SLS_OTEL_RESOURCE_ATTRIBUTES_ORG_ID,
    DEFAULT_SLS_OTEL_RESOURCE_ATTRIBUTES_SERVICE_NAME,
    DEFAULT_SLS_OTEL_RESOURCE_ATTRIBUTES_STAGE,
)
from serverless_aws_lambda_otel_extension.shared.environment import AWS_LAMBDA_RUNTIME_API
from serverless_aws_lambda_otel_extension.shared.settings import settings


def map_otel_resource_attributes(resource_attributes: str) -> Dict[str, str]:
    return dict([assignment.split("=", maxsplit=1) for assignment in resource_attributes.split(",")])


def build_otel_resource_attributes() -> str:

    resource_attributes: Dict[str, str] = {}

    resource_attributes.update(map_otel_resource_attributes(os.getenv(OTEL_RESOURCE_ATTRIBUTES_ENV_VAR, "")))
    resource_attributes.update(map_otel_resource_attributes(os.getenv(SLS_OTEL_RESOURCE_ATTRIBUTES_ENV_VAR, "")))

    resource_attributes.setdefault(
        SLS_OTEL_RESOURCE_ATTRIBUTES_SERVICE_NAME_VAR,
        DEFAULT_SLS_OTEL_RESOURCE_ATTRIBUTES_SERVICE_NAME,
    )
    resource_attributes.setdefault(
        SLS_OTEL_RESOURCE_ATTRIBUTES_STAGE_VAR,
        DEFAULT_SLS_OTEL_RESOURCE_ATTRIBUTES_STAGE,
    )
    resource_attributes.setdefault(
        SLS_OTEL_RESOURCE_ATTRIBUTES_ORG_ID_VAR,
        DEFAULT_SLS_OTEL_RESOURCE_ATTRIBUTES_ORG_ID,
    )

    return ",".join(["=".join(item) for item in resource_attributes.items()])


def build_extensions_api_register_url():
    return "http://{}/{}".format(
        AWS_LAMBDA_RUNTIME_API,
        EXTENSIONS_API_REGISTER_PATH,
    )


def build_extensions_api_next_url():
    return "http://{}/{}".format(
        AWS_LAMBDA_RUNTIME_API,
        EXTENSIONS_API_EVENT_NEXT_PATH,
    )


def build_logs_api_register_url():
    return "http://{}/{}".format(
        AWS_LAMBDA_RUNTIME_API,
        LOGS_API_PATH,
    )


def build_log_server_url():
    return "http://{}:{}/".format(settings.log_server_host, settings.log_server_port)


def build_otel_server_url():
    return "http://{}:{}/".format(settings.otel_server_host, settings.otel_server_port)
