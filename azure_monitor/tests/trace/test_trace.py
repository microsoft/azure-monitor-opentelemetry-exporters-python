# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


import json
import os
import shutil
import unittest
from unittest import mock

# pylint: disable=import-error
from opentelemetry.sdk.trace import Span
from opentelemetry.trace import Link, SpanContext, SpanKind
from opentelemetry.trace.status import Status, StatusCanonicalCode

from azure_monitor.protocol import Envelope
from azure_monitor.trace import AzureMonitorSpanExporter
from azure_monitor.utils import ExportResult, Options

TEST_FOLDER = os.path.abspath(".test.exporter.trace")


def setUpModule():
    os.makedirs(TEST_FOLDER)


def tearDownModule():
    shutil.rmtree(TEST_FOLDER)


def throw(exc_type, *args, **kwargs):
    def func(*_args, **_kwargs):
        raise exc_type(*args, **kwargs)

    return func


# pylint: disable=import-error
class TestAzureExporter(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        os.environ.clear()
        os.environ[
            "APPINSIGHTS_INSTRUMENTATIONKEY"
        ] = "1234abcd-5678-4efa-8abc-1234567890ab"

    def test_constructor(self):
        """Test the constructor."""
        exporter = AzureMonitorSpanExporter(
            instrumentation_key="4321abcd-5678-4efa-8abc-1234567890ab"
        )
        self.assertIsInstance(exporter.options, Options)
        self.assertEqual(
            exporter.options.instrumentation_key,
            "4321abcd-5678-4efa-8abc-1234567890ab",
        )

    def test_export_empty(self):
        exporter = AzureMonitorSpanExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        exporter.export([])
        self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    @mock.patch("azure_monitor.trace.logger")
    def test_export_exception(self, mock_logger):
        exporter = AzureMonitorSpanExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        exporter.export([None])
        mock_logger.exception.assert_called()

    @mock.patch(
        "azure_monitor.trace.AzureMonitorSpanExporter.span_to_envelope"
    )  # noqa: E501
    def test_export_failure(self, span_to_envelope_mock):
        span_to_envelope_mock.return_value = ["bar"]
        exporter = AzureMonitorSpanExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        with mock.patch(
            "azure_monitor.trace.AzureMonitorSpanExporter._transmit"
        ) as transmit:  # noqa: E501
            test_span = Span(
                name="test",
                context=SpanContext(
                    trace_id=36873507687745823477771305566750195431,
                    span_id=12030755672171557338,
                ),
            )
            test_span.start()
            test_span.end()
            transmit.return_value = ExportResult.FAILED_RETRYABLE
            exporter.export([test_span])
        self.assertEqual(len(os.listdir(exporter.storage.path)), 1)
        self.assertIsNone(exporter.storage.get())

    @mock.patch(
        "azure_monitor.trace.AzureMonitorSpanExporter.span_to_envelope"
    )  # noqa: E501
    def test_export_success(self, span_to_envelope_mock):
        span_to_envelope_mock.return_value = ["bar"]
        exporter = AzureMonitorSpanExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        with mock.patch(
            "azure_monitor.trace.AzureMonitorSpanExporter._transmit"
        ) as transmit:  # noqa: E501
            transmit.return_value = 0
            exporter.export([])
            exporter.export(["foo"])
            self.assertEqual(len(os.listdir(exporter.storage.path)), 0)
            exporter.export(["foo"])
            self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    def test_span_to_envelope(self):
        options = {
            "instrumentation_key": "12345678-1234-5678-abcd-12345678abcd"
        }
        exporter = AzureMonitorSpanExporter(**options)

        parent_span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557338,
            ),
        )

        start_time = 1575494316027613500
        end_time = start_time + 1001000000

        # SpanKind.CLIENT HTTP
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.RemoteDependency"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.name, "GET//wiki/Rabbit")
        self.assertEqual(
            envelope.data.base_data.data,
            "https://www.wikipedia.org/wiki/Rabbit",
        )
        self.assertEqual(envelope.data.base_data.target, "www.wikipedia.org")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.result_code, "200")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.type, "HTTP")
        self.assertEqual(envelope.data.base_type, "RemoteDependencyData")

        # SpanKind.CLIENT unknown type
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={},
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.RemoteDependency"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.name, "test")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.type, None)
        self.assertEqual(envelope.data.base_type, "RemoteDependencyData")

        # SpanKind.CLIENT missing method
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.RemoteDependency"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.name, "test")
        self.assertEqual(
            envelope.data.base_data.data,
            "https://www.wikipedia.org/wiki/Rabbit",
        )
        self.assertEqual(envelope.data.base_data.target, "www.wikipedia.org")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.result_code, "200")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.type, "HTTP")
        self.assertEqual(envelope.data.base_type, "RemoteDependencyData")

        # SpanKind.SERVER HTTP - 200 request
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.path": "/wiki/Rabbit",
                "http.route": "/wiki/Rabbit",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.Request"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(
            envelope.tags["ai.operation.name"], "GET /wiki/Rabbit"
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.response_code, "200")
        self.assertEqual(envelope.data.base_data.name, "GET /wiki/Rabbit")
        self.assertEqual(envelope.data.base_data.success, True)
        self.assertEqual(
            envelope.data.base_data.url,
            "https://www.wikipedia.org/wiki/Rabbit",
        )
        self.assertEqual(envelope.data.base_type, "RequestData")

        # SpanKind.SERVER HTTP - Failed request
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.path": "/wiki/Rabbit",
                "http.route": "/wiki/Rabbit",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.Request"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(
            envelope.tags["ai.operation.name"], "GET /wiki/Rabbit"
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.response_code, "400")
        self.assertEqual(envelope.data.base_data.name, "GET /wiki/Rabbit")
        self.assertEqual(envelope.data.base_data.success, False)
        self.assertEqual(
            envelope.data.base_data.url,
            "https://www.wikipedia.org/wiki/Rabbit",
        )
        self.assertEqual(envelope.data.base_type, "RequestData")

        # SpanKind.SERVER unknown type
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.path": "/wiki/Rabbit",
                "http.route": "/wiki/Rabbit",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.Request"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_type, "RequestData")

        # SpanKind.INTERNAL
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=None,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={"key1": "value1"},
            events=None,
            links=[],
            kind=SpanKind.INTERNAL,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.RemoteDependency"
        )
        self.assertRaises(
            KeyError, lambda: envelope.tags["ai.operation.parentId"]
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.name, "test")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.type, "InProc")
        self.assertEqual(envelope.data.base_type, "RemoteDependencyData")

        # Attributes
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
                "test": "asd",
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(len(envelope.data.base_data.properties), 2)
        self.assertEqual(
            envelope.data.base_data.properties["component"], "http"
        )
        self.assertEqual(envelope.data.base_data.properties["test"], "asd")

        # Links
        links = []
        links.append(
            Link(
                context=SpanContext(
                    trace_id=36873507687745823477771305566750195432,
                    span_id=12030755672171557338,
                )
            )
        )
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
            },
            events=None,
            links=links,
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(len(envelope.data.base_data.properties), 2)
        json_dict = json.loads(
            envelope.data.base_data.properties["_MS.links"]
        )[0]
        self.assertEqual(json_dict["id"], "a6f5d48acb4d31da")

        # Status
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 500,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.response_code, "500")
        self.assertFalse(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 500,
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.result_code, "500")
        self.assertFalse(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.response_code, "0")
        self.assertTrue(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.result_code, "0")
        self.assertTrue(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.UNKNOWN)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.response_code, "2")
        self.assertFalse(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.UNKNOWN)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.result_code, "2")
        self.assertFalse(envelope.data.base_data.success)

        # Server route attribute
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.method": "GET",
                "http.route": "/wiki/Rabbit",
                "http.path": "/wiki/Rabbitz",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(
            envelope.data.base_data.properties["request.name"],
            "GET /wiki/Rabbit",
        )
        self.assertEqual(
            envelope.data.base_data.properties["request.url"],
            "https://www.wikipedia.org/wiki/Rabbit",
        )

        # Server method attribute missing
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.path": "/wiki/Rabbitz",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter.span_to_envelope(span)
        self.assertIsNone(envelope.data.base_data.name)

        # Server route attribute missing
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.method": "GET",
                "http.path": "/wiki/Rabbitz",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter.span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.name, "GET")
        self.assertEqual(
            envelope.data.base_data.properties["request.name"],
            "GET /wiki/Rabbitz",
        )
        self.assertEqual(
            envelope.data.base_data.properties["request.url"],
            "https://www.wikipedia.org/wiki/Rabbit",
        )

        # Server route and path attribute missing
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter.span_to_envelope(span)
        self.assertIsNone(
            envelope.data.base_data.properties.get("request.name")
        )
        self.assertEqual(
            envelope.data.base_data.properties["request.url"],
            "https://www.wikipedia.org/wiki/Rabbit",
        )

        # Server http.url missing
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.method": "GET",
                "http.route": "/wiki/Rabbit",
                "http.path": "/wiki/Rabbitz",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter.span_to_envelope(span)
        self.assertIsNone(envelope.data.base_data.url)
        self.assertIsNone(
            envelope.data.base_data.properties.get("request.url")
        )
