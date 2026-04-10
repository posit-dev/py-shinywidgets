import decimal
import json
from datetime import date, datetime, timezone

import pytest
import shinywidgets._serialization as ser
from shinywidgets._serialization import json_default, json_packer


def test_json_default_datetime_aware_utc_endswith_z() -> None:
    dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    out = json_default(dt)
    assert isinstance(out, str)
    assert out.endswith("Z")
    assert "+00:00" not in out


def test_json_default_datetime_naive_warns_and_uses_local_tz(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Make this deterministic across developer machines/CI.
    monkeypatch.setattr(ser, "tzlocal", lambda: timezone.utc)

    dt = datetime(2020, 1, 2, 3, 4, 5)
    with pytest.warns(DeprecationWarning):
        out = json_default(dt)

    assert isinstance(out, str)
    assert out.endswith("Z")


def test_json_default_date_bytes_iterable_and_numbers() -> None:
    assert json_default(date(2020, 1, 2)) == "2020-01-02"
    assert json_default(b"hi") == "aGk=\n"

    gen = (x for x in [1, 2])
    assert json_default(gen) == [1, 2]

    assert json_default(1) == 1
    assert json_default(1.25) == 1.25
    assert json_default(decimal.Decimal("1.5")) == 1.5

    with pytest.raises(TypeError) as excinfo:
        json_default(object())
    assert "is not JSON serializable" in str(excinfo.value)


def test_json_packer_returns_str_and_round_trips() -> None:
    packed = json_packer({"a": 1})
    assert isinstance(packed, str)
    assert json.loads(packed) == {"a": 1}


def test_json_packer_rejects_nan() -> None:
    with pytest.raises(ValueError):
        json_packer({"x": float("nan")})
