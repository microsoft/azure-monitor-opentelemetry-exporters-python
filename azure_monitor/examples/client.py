# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License...
import requests

from azure_monitor import AzureMonitorSpanExporter
from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.sdk.trace import TracerSource
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
tracer = trace.tracer_source().get_tracer(__name__)
http_requests.enable(trace.tracer_source())
span_processor = BatchExportSpanProcessor(
    AzureMonitorSpanExporter(instrumentation_key="<INSTRUMENTATION KEY HERE>")
)
trace.tracer_source().add_span_processor(span_processor)

response = requests.get(url="http://127.0.0.1:8080/")
span_processor.shutdown()
