# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import json
import os
import shutil
import unittest

import mock

from azure_monitor.exporter import BaseExporter
from azure_monitor.protocol import Data, Envelope
from azure_monitor.utils import Options

TEST_FOLDER = os.path.abspath(".test.exporter")


def setUpModule():
    os.makedirs(TEST_FOLDER)


def tearDownModule():
    shutil.rmtree(TEST_FOLDER)


def throw(exc_type, *args, **kwargs):
    def func(*_args, **_kwargs):
        raise exc_type(*args, **kwargs)

    return func


class MockResponse(object):
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


class MockTransport(object):
    def __init__(self, exporter=None):
        self.export_called = False
        self.exporter = exporter

    def export(self, datas):
        self.export_called = True


# pylint: disable=W0212
class TestBaseExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ[
            "APPINSIGHTS_INSTRUMENTATIONKEY"
        ] = "1234abcd-5678-4efa-8abc-1234567890ab"

    def test_constructor(self):
        """Test the constructor."""
        base = BaseExporter(
            instrumentation_key="4321abcd-5678-4efa-8abc-1234567890ab",
            storage_maintenance_period=2,
            storage_max_size=3,
            storage_path=os.path.join(TEST_FOLDER, self.id()),
            storage_retention_period=4,
            timeout=5,
        )
        self.assertIsInstance(base.options, Options)
        self.assertEqual(
            base.options.instrumentation_key,
            "4321abcd-5678-4efa-8abc-1234567890ab",
        )
        self.assertEqual(base.options.storage_maintenance_period, 2)
        self.assertEqual(base.options.storage_max_size, 3)
        self.assertEqual(base.options.storage_retention_period, 4)
        self.assertEqual(base.options.timeout, 5)
        self.assertEqual(
            base.options.storage_path, os.path.join(TEST_FOLDER, self.id())
        )

    def test_constructor_wrong_options(self):
        """Test the constructor with wrong options."""
        with self.assertRaises(TypeError):
            base = BaseExporter(
                something_else=6,
                storage_path=os.path.join(TEST_FOLDER, self.id()),
            )

    def test_telemetry_processor_add(self):
        base = BaseExporter(storage_path=os.path.join(TEST_FOLDER, self.id()))
        base.add_telemetry_processor(lambda: True)
        self.assertEqual(len(base._telemetry_processors), 1)

    def test_telemetry_processor_clear(self):
        base = BaseExporter(storage_path=os.path.join(TEST_FOLDER, self.id()))
        base.add_telemetry_processor(lambda: True)
        self.assertEqual(len(base._telemetry_processors), 1)
        base.clear_telemetry_processors()
        self.assertEqual(len(base._telemetry_processors), 0)

    def test_telemetry_processor_apply(self):
        base = BaseExporter(storage_path=os.path.join(TEST_FOLDER, self.id()))

        def callback_function(envelope):
            envelope.data.base_type += "_world"

        base.add_telemetry_processor(callback_function)
        envelope = Envelope(data=Data(base_type="type1"))
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.data.base_type, "type1_world")

    def test_telemetry_processor_apply_multiple(self):
        base = BaseExporter(storage_path=os.path.join(TEST_FOLDER, self.id()))
        base._telemetry_processors = []

        def callback_function(envelope):
            envelope.data.base_type += "_world"

        def callback_function2(envelope):
            envelope.data.base_type += "_world2"

        base.add_telemetry_processor(callback_function)
        base.add_telemetry_processor(callback_function2)
        envelope = Envelope(data=Data(base_type="type1"))
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.data.base_type, "type1_world_world2")

    def test_telemetry_processor_apply_exception(self):
        base = BaseExporter(storage_path=os.path.join(TEST_FOLDER, self.id()))

        def callback_function(envelope):
            raise ValueError()

        def callback_function2(envelope):
            envelope.data.base_type += "_world2"

        base.add_telemetry_processor(callback_function)
        base.add_telemetry_processor(callback_function2)
        envelope = Envelope(data=Data(base_type="type1"))
        base.apply_telemetry_processors([envelope])
        self.assertEqual(envelope.data.base_type, "type1_world2")

    def test_telemetry_processor_apply_not_accepted(self):
        base = BaseExporter(storage_path=os.path.join(TEST_FOLDER, self.id()))

        def callback_function(envelope):
            return envelope.data.base_type == "type2"

        base.add_telemetry_processor(callback_function)
        envelope = Envelope(data=Data(base_type="type1"))
        envelope2 = Envelope(data=Data(base_type="type2"))
        envelopes = base.apply_telemetry_processors([envelope, envelope2])
        self.assertEqual(len(envelopes), 1)
        self.assertEqual(envelopes[0].data.base_type, "type2")

    def test_transmission_nothing(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        with mock.patch("requests.post") as post:
            post.return_value = None
            exporter._transmit_from_storage()

    def test_transmission_pre_exception(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post", throw(Exception)):
            exporter._transmit_from_storage()
        self.assertIsNone(exporter.storage.get())
        self.assertEqual(len(os.listdir(exporter.storage.path)), 1)

    @mock.patch("requests.post", return_value=mock.Mock())
    def test_transmission_lease_failure(self, requests_mock):
        requests_mock.return_value = MockResponse(200, "unknown")
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch(
            "azure_monitor.storage.LocalFileBlob.lease"
        ) as lease:  # noqa: E501
            lease.return_value = False
            exporter._transmit_from_storage()
        self.assertTrue(exporter.storage.get())

    def test_transmission_post_exception(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post") as post:
            post.return_value = MockResponse(200, None)
            del post.return_value.text
            exporter._transmit_from_storage()
        self.assertIsNone(exporter.storage.get())
        self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    def test_transmission_200(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post") as post:
            post.return_value = MockResponse(200, "unknown")
            exporter._transmit_from_storage()
        self.assertIsNone(exporter.storage.get())
        self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    def test_transmission_206(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post") as post:
            post.return_value = MockResponse(206, "unknown")
            exporter._transmit_from_storage()
        self.assertIsNone(exporter.storage.get())
        self.assertEqual(len(os.listdir(exporter.storage.path)), 1)

    def test_transmission_206_500(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        test_envelope = Envelope(name="testEnvelope")
        envelopes_to_export = map(
            lambda x: x.to_dict(),
            tuple([Envelope(), Envelope(), test_envelope]),
        )
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post") as post:
            post.return_value = MockResponse(
                206,
                json.dumps(
                    {
                        "itemsReceived": 5,
                        "itemsAccepted": 3,
                        "errors": [
                            {"index": 0, "statusCode": 400, "message": ""},
                            {
                                "index": 2,
                                "statusCode": 500,
                                "message": "Internal Server Error",
                            },
                        ],
                    }
                ),
            )
            exporter._transmit_from_storage()
        self.assertEqual(len(os.listdir(exporter.storage.path)), 1)
        self.assertEqual(
            exporter.storage.get().get()[0]["name"], "testEnvelope"
        )

    def test_transmission_206_no_retry(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post") as post:
            post.return_value = MockResponse(
                206,
                json.dumps(
                    {
                        "itemsReceived": 3,
                        "itemsAccepted": 2,
                        "errors": [
                            {"index": 0, "statusCode": 400, "message": ""}
                        ],
                    }
                ),
            )
            exporter._transmit_from_storage()
        self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    def test_transmission_206_bogus(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post") as post:
            post.return_value = MockResponse(
                206,
                json.dumps(
                    {
                        "itemsReceived": 5,
                        "itemsAccepted": 3,
                        "errors": [{"foo": 0, "bar": 1}],
                    }
                ),
            )
            exporter._transmit_from_storage()
        self.assertIsNone(exporter.storage.get())
        self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    def test_transmission_400(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post") as post:
            post.return_value = MockResponse(400, "{}")
            exporter._transmit_from_storage()
        self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    def test_transmission_500(self):
        exporter = BaseExporter(
            storage_path=os.path.join(TEST_FOLDER, self.id())
        )
        envelopes_to_export = map(lambda x: x.to_dict(), tuple([Envelope()]))
        exporter.storage.put(envelopes_to_export)
        with mock.patch("requests.post") as post:
            post.return_value = MockResponse(500, "{}")
            exporter._transmit_from_storage()
        self.assertIsNone(exporter.storage.get())
        self.assertEqual(len(os.listdir(exporter.storage.path)), 1)
