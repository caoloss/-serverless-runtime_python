import os

from serverless_aws_lambda_otel_extension.shared.constants import (
    SLS_LOG_SERVER_HOST_ENV_VAR,
    SLS_LOG_SERVER_PORT_ENV_VAR,
    SLS_OTEL_SERVER_HOST_ENV_VAR,
    SLS_OTEL_SERVER_PORT_ENV_VAR,
)
from serverless_aws_lambda_otel_extension.shared.defaults import (
    DEFAULT_SLS_LOG_SERVER_HOST,
    DEFAULT_SLS_LOG_SERVER_PORT,
    DEFAULT_SLS_OTEL_SERVER_HOST,
    DEFAULT_SLS_OTEL_SERVER_PORT,
)


class Settings:
    @property
    def otel_server_host(self) -> str:
        return os.getenv(SLS_OTEL_SERVER_HOST_ENV_VAR) or DEFAULT_SLS_OTEL_SERVER_HOST

    @property
    def otel_server_port(self) -> int:
        return int(os.getenv(SLS_OTEL_SERVER_PORT_ENV_VAR) or DEFAULT_SLS_OTEL_SERVER_PORT)

    @property
    def log_server_host(self) -> str:
        return os.getenv(SLS_LOG_SERVER_HOST_ENV_VAR) or DEFAULT_SLS_LOG_SERVER_HOST

    @property
    def log_server_port(self) -> int:
        return int(os.getenv(SLS_LOG_SERVER_PORT_ENV_VAR) or DEFAULT_SLS_LOG_SERVER_PORT)


# Singleton instance of the settings
settings = Settings()
