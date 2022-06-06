import os

from serverless_aws_lambda_otel_extension.shared.constants import AWS_LAMBDA_RUNTIME_API_ENV_VAR, TEST_DRY_LOG_ENV_VAR

AWS_LAMBDA_RUNTIME_API = os.getenv(AWS_LAMBDA_RUNTIME_API_ENV_VAR)
TEST_DRY_LOG = os.getenv(TEST_DRY_LOG_ENV_VAR)
