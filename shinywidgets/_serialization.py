import decimal
import json
import numbers
import warnings
from binascii import b2a_base64
from datetime import datetime
from typing import Iterable

from dateutil.tz import tzlocal


# Same as `from jupyter_client.session import json_packer` (i.e., Jupyter's
# default JSON serializer), except this returns a string not bytes, and doesn't
# do cleaning/exception handling (which is no longer necessary now that json_default
# handles bytes https://github.com/ipython/ipykernel/pull/708)
#
# N.B. the serializer inside jupyter_client.session.Session is customizable, but
# it seems like we can avoid supporting that, and thus avoid a bunch of run-time
# sanity checks.
def json_packer(obj: object) -> str:
    return json.dumps(
        obj,
        default=json_default,
        ensure_ascii=False,
        allow_nan=False,
    )


def json_default(obj: object) -> object:
    if isinstance(obj, datetime):
        obj = _ensure_tzinfo(obj)
        return obj.isoformat().replace("+00:00", "Z")

    if isinstance(obj, bytes):
        return b2a_base64(obj).decode("ascii")

    if isinstance(obj, Iterable):
        return list(
            obj  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        )

    if isinstance(obj, numbers.Integral):
        return int(obj)

    if isinstance(obj, numbers.Real):
        return float(obj)

    if isinstance(obj, decimal.Decimal):
        return float(obj)

    raise TypeError("%r is not JSON serializable" % obj)


def _ensure_tzinfo(dt: datetime) -> datetime:
    """Ensure a datetime object has tzinfo (if none is present, add it)"""
    if not dt.tzinfo:
        # No more naïve datetime objects!
        warnings.warn(
            "Interpreting naive datetime as local %s. Please add timezone info to timestamps."
            % dt,
            DeprecationWarning,
            stacklevel=4,
        )
        dt = dt.replace(tzinfo=tzlocal())
    return dt
