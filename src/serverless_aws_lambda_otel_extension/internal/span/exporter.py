from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Singleton instance of the memory exporter
in_memory_span_exporter = InMemorySpanExporter()
