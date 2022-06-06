from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from serverless_aws_lambda_otel_extension.internal.span.exporter import in_memory_span_exporter


class ServerlessSpanProcessor(SimpleSpanProcessor):
    pass


# Singleton instance of the span processor
serverless_span_processor = ServerlessSpanProcessor(in_memory_span_exporter)
