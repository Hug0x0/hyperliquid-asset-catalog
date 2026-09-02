import json
import logging

from hl_asset_catalog.observability import JsonFormatter, redact_log


def test_json_formatter_contract_and_redaction() -> None:
    record = logging.LogRecord(
        "catalog",
        logging.INFO,
        __file__,
        1,
        "url=https://x.test?token=hunter2",
        (),
        None,
    )
    record.operation = "fetch"
    record.correlation_id = "stable-id"
    payload = json.loads(JsonFormatter().format(record))
    assert set(payload) == {
        "timestamp",
        "level",
        "component",
        "operation",
        "correlation_id",
        "message",
    }
    assert payload["message"] == "url=https://x.test?token=<redacted>"


def test_redact_log_leaves_safe_text_unchanged() -> None:
    assert redact_log("assets=12") == "assets=12"
