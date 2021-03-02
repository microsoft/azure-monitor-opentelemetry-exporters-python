> **This repository has been moved to the [Azure SDK for Python](https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/monitor/azure-monitor-opentelemetry-exporter) repository.** In order to improve discoverability and share common dependencies/tests, the OpenTelemetry Azure Monitor exporters for Python has moved to a common location containing all Azure SDKs. Please submit all issues and inquiries in that repository.

# OpenTelemetry Azure Monitor

[![Gitter chat](https://img.shields.io/gitter/room/Microsoft/azure-monitor-python)](https://gitter.im/Microsoft/azure-monitor-python)
[![Build status](https://travis-ci.org/microsoft/opentelemetry-azure-monitor-python.svg?branch=master)](https://travis-ci.org/microsoft/opentelemetry-azure-monitor-python)

## Installation

```sh
pip install opentelemetry-azure-monitor
```

## Documentation

The online documentation is available at https://opentelemetry-azure-monitor-python.readthedocs.io/.

## Usage


### Trace

The **Azure Monitor Span Exporter** allows you to export [OpenTelemetry](https://opentelemetry.io/) traces to [Azure Monitor](https://docs.microsoft.com/azure/azure-monitor/).

This example shows how to send a span "hello" to Azure Monitor.

* Create an Azure Monitor resource and get the instrumentation key, more information can be found [here](https://docs.microsoft.com/azure/azure-monitor/app/create-new-resource).
* Place your instrumentation key in a `connection string` and directly into your code.
* Alternatively, you can specify your `connection string` in an environment variable ``APPLICATIONINSIGHTS_CONNECTION_STRING``.

```python
from azure_monitor import AzureMonitorSpanExporter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# SpanExporter receives the spans and send them to the target location
exporter = AzureMonitorSpanExporter(
    connection_string='InstrumentationKey=<your-ikey-here>',
)

span_processor = BatchExportSpanProcessor(exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

with tracer.start_as_current_span('hello'):
    print('Hello World!')
```

#### Instrumentations

OpenTelemetry also supports several [instrumentations](https://github.com/open-telemetry/opentelemetry-python/tree/master/instrumentation) which allows to instrument with third party libraries.

This example shows how to instrument with the [requests](https://2.python-requests.org/en/master/)_ library.

* Create an Azure Monitor resource and get the instrumentation key, more information can be found [here](https://docs.microsoft.com/azure/azure-monitor/app/create-new-resource).
* Install the `requests` integration package using ``pip install opentelemetry-ext-http-requests``.
* Place your instrumentation key in a `connection string` and directly into your code.
* Alternatively, you can specify your `connection string` in an environment variable ``APPLICATIONINSIGHTS_CONNECTION_STRING``.

```python
import requests

from azure_monitor import AzureMonitorSpanExporter
from opentelemetry import trace
from opentelemetry.ext.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()

exporter = AzureMonitorSpanExporter(
    connection_string='InstrumentationKey=<your-ikey-here>',
)
span_processor = BatchExportSpanProcessor(exporter)
tracer_provider.add_span_processor(span_processor)

RequestsInstrumentor().instrument()

# This request will be traced
response = requests.get(url="https://azure.microsoft.com/")
```

#### Modifying Traces

* You can pass a callback function to the exporter to process telemetry before it is exported.
* Your callback function can return `False` if you do not want this envelope exported.
* Your callback function must accept an [envelope](https://github.com/microsoft/opentelemetry-exporters-python/blob/master/azure_monitor/src/azure_monitor/protocol.py#L80) data type as its parameter.
* You can see the schema for Azure Monitor data types in the envelopes [here](https://github.com/microsoft/opentelemetry-exporters-python/blob/master/azure_monitor/src/azure_monitor/protocol.py).
* The `AzureMonitorSpanExporter` handles `Data` data types.

```python
from azure_monitor import AzureMonitorSpanExporter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

# Callback function to add os_type: linux to span properties
def callback_function(envelope):
    envelope.data.baseData.properties['os_type'] = 'linux'
    return True

exporter = AzureMonitorSpanExporter(
    connection_string='InstrumentationKey=<your-ikey-here>'
)
# This line will modify telemetry
exporter.add_telemetry_processor(callback_function)

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
span_processor = BatchExportSpanProcessor(exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

with tracer.start_as_current_span('hello'):
    print('Hello World!')
```

### Metrics

The **Azure Monitor Metrics Exporter** allows you to export metrics to [Azure Monitor](https://docs.microsoft.com/azure/azure-monitor/).

This example shows how to track a counter metric and send it as telemetry every export interval.

* Create an Azure Monitor resource and get the instrumentation key, more information can be found [here](https://docs.microsoft.com/azure/azure-monitor/app/create-new-resource).
* Place your instrumentation key in a `connection string` and directly into your code.
* Alternatively, you can specify your `connection string` in an environment variable ``APPLICATIONINSIGHTS_CONNECTION_STRING``.

```python
from azure_monitor import AzureMonitorMetricsExporter
from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export.controller import PushController

metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__)
exporter = AzureMonitorMetricsExporter(
    connection_string='InstrumentationKey=<your-ikey-here>'
)
controller = PushController(meter, exporter, 5)

requests_counter = meter.create_metric(
    name="requests",
    description="number of requests",
    unit="1",
    value_type=int,
    metric_type=Counter,
    label_keys=("environment",),
)

testing_labels = {"environment": "testing"}

requests_counter.add(25, testing_labels)
input("...")
```
