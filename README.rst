OpenTelemetry Azure Monitor Exporters
=====================================

.. image:: https://badges.gitter.im/Microsoft/azure-monitor-exporters.svg
   :alt: Join the chat at https://gitter.im/Microsoft/azure-monitor-exporters
   :target: https://gitter.im/Microsoft/azure-monitor-exporters?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-azure-monitor-exporter.svg
   :target: https://pypi.org/project/opentelemetry-azure-monitor-exporter/

Installation
------------

::

    pip install opentelemetry-azure-monitor-exporter

Usage
-----

Trace
~~~~~

The **Azure Monitor Trace Exporter** allows you to export `OpenTelemetry`_ traces to `Azure Monitor`_.

This example shows how to send a span "hello" to Azure Monitor.

* Create an Azure Monitor resource and get the instrumentation key, more information can be found `here <https://docs.microsoft.com/azure/azure-monitor/app/create-new-resource>`_.
* Place your instrumentation key in a `connection string` and directly into your code.
* Alternatively, you can specify your `connection string` in an environment variable ``APPLICATIONINSIGHTS_CONNECTION_STRING``.

 .. code:: python

    from azure_monitor import AzureMonitorSpanExporter
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    # The preferred tracer implementation must be set, as the opentelemetry-api
    # defines the interface with a no-op implementation.
    trace.set_preferred_tracer_provider_implementation(lambda T: TracerProvider())

    # We tell OpenTelemetry who it is that is creating spans. In this case, we have
    # no real name (no setup.py), so we make one up. If we had a version, we would
    # also specify it here.
    tracer = trace.get_tracer(__name__)

    exporter = AzureMonitorSpanExporter(
        connection_string='InstrumentationKey=99c42f65-1656-4c41-afde-bd86b709a4a7',
    )

    # SpanExporter receives the spans and send them to the target location.
    span_processor = BatchExportSpanProcessor(exporter)
    trace.tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span('hello'):
        print('Hello World!')

Integrations
############

OpenTelemetry also supports several `integrations <https://github.com/open-telemetry/opentelemetry-python/tree/master/ext>`_ which allows to integrate with third party libraries.

This example shows how to integrate with the `requests <https://2.python-requests.org/en/master/>`_ library.

* Create an Azure Monitor resource and get the instrumentation key, more information can be found `here <https://docs.microsoft.com/azure/azure-monitor/app/create-new-resource>`_.
* Install the `requests integration package using ``pip install opentelemetry-ext-http-requests``.
* Place your instrumentation key in a `connection string` and directly into your code.
* Alternatively, you can specify your `connection string` in an environment variable ``APPLICATIONINSIGHTS_CONNECTION_STRING``.

.. code:: python

    import requests

    from azure_monitor import AzureMonitorSpanExporter
    from opentelemetry import trace
    from opentelemetry.ext import http_requests
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchExportSpanProcessor,
        ConsoleSpanExporter,
    )

    # The preferred tracer implementation must be set, as the opentelemetry-api
    # defines the interface with a no-op implementation.
    trace.set_preferred_tracer_provider_implementation(lambda T: TracerProvider())
    tracer_provider = trace.tracer_provider()

    exporter = AzureMonitorSpanExporter(
            connection_string='InstrumentationKey=99c42f65-1656-4c41-afde-bd86b709a4a7',
        )
    span_processor = BatchExportSpanProcessor(exporter)
    tracer_provider.add_span_processor(span_processor)

    http_requests.enable(tracer_provider)
    response = requests.get(url="https://azure.microsoft.com/")

Modifying Traces
################

* You can pass a callback function to the exporter to process telemetry before it is exported.
* Your callback function can return `False` if you do not want this envelope exported.
* Your callback function must accept an [envelope](https://github.com/microsoft/opentelemetry-exporters-python/blob/master/azure_monitor/src/azure_monitor/protocol.py#L80) data type as its parameter.
* You can see the schema for Azure Monitor data types in the envelopes [here](https://github.com/microsoft/opentelemetry-exporters-python/blob/master/azure_monitor/src/azure_monitor/protocol.py).
* The `AzureMonitorSpanExporter` handles `Data` data types.

.. code:: python

    from azure_monitor import AzureMonitorSpanExporter
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    # Callback function to add os_type: linux to span properties
    def callback_function(envelope):
        envelope.data.baseData.properties['os_type'] = 'linux'
        return True

    exporter = AzureMonitorSpanExporter(
        connection_string='InstrumentationKey=99c42f65-1656-4c41-afde-bd86b709a4a7'
    )
    exporter.add_telemetry_processor(callback_function)

    trace.set_preferred_tracer_provider_implementation(lambda T: TracerProvider())
    tracer = trace.get_tracer(__name__)
    span_processor = BatchExportSpanProcessor(exporter)
    trace.tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span('hello'):
        print('Hello World!')

References
----------

* `Azure Monitor <https://docs.microsoft.com/azure/azure-monitor/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry Python Client <https://github.com/open-telemetry/opentelemetry-python>`_

