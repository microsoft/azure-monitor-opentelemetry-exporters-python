# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import json
import logging
from typing import Sequence
from urllib.parse import urlparse

from opentelemetry.metrics import Counter, Measure, Metric
from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExporter,
    MetricsExportResult,
)
from opentelemetry.sdk.util import ns_to_iso_str

from azure_monitor import protocol, utils
from azure_monitor.exporter import BaseExporter

logger = logging.getLogger(__name__)


class AzureMonitorMetricsExporter(BaseExporter, MetricsExporter):
    def __init__(self, **options):
        super(AzureMonitorMetricsExporter, self).__init__(**options)

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> MetricsExportResult:
        envelopes = list(map(self.metric_to_envelope, metric_records))
        envelopes = list(
            map(
                lambda x: x.to_dict(),
                self.apply_telemetry_processors(envelopes),
            )
        )
        try:
            result = self._transmit(envelopes)
            if result == MetricsExportResult.FAILED_RETRYABLE:
                self.storage.put(envelopes, result)
            if result == utils.ExportResult.SUCCESS:
                # Try to send any cached events
                self._transmit_from_storage()
            return utils.get_metrics_export_result(result)
        except Exception:
            logger.exception("Exception occurred while exporting the data.")

    def metric_to_envelope(
        self, metric_record: MetricRecord
    ) -> protocol.Envelope:

        if not metric_record:
            return None
        envelope = protocol.Envelope(
            ikey=self.options.instrumentation_key,
            tags=dict(utils.azure_monitor_context),
            time=ns_to_iso_str(
                metric_record.metric.get_handle(
                    metric_record.label_set
                ).last_update_timestamp
            ),
        )
        envelope.name = "Microsoft.ApplicationInsights.Metric"

        data_point = protocol.DataPoint(
            ns=metric_record.metric.description,
            name=metric_record.metric.name,
            value=metric_record.aggregator.checkpoint,
            kind=protocol.DataPointType.MEASUREMENT.value,
        )

        properties = {}
        for label_tuple in metric_record.label_set.labels:
            properties[label_tuple[0]] = label_tuple[1]
        data = protocol.MetricData(metrics=[data_point], properties=properties)
        envelope.data = protocol.Data(base_data=data, base_type="MetricData")
        return envelope
