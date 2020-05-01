import csv
import io
import json
import pathlib
import shutil
import tarfile
import tempfile
import time
import uuid

import arrow

from encapsia_api import EncapsiaApi, discover_credentials


__all__ = ["get_api_from_api_or_host", "make_uuid", "typed_csv_reader"]


def get_api_from_api_or_host(api_or_host):
    """Convenience to support functions taking either host name or pre-existing api."""
    if isinstance(api_or_host, EncapsiaApi):
        return api_or_host
    else:
        url, token = discover_credentials(api_or_host)
        return EncapsiaApi(url, token)


def make_uuid():
    """Generate and return new uuid typically used in encapsia."""
    return uuid.uuid4().hex


def typed_csv_reader(data):
    """Read CSV with typing info in the column names into a yielded dict per row."""
    BOOLEAN_LOOKUP = {
        "yes": True,
        "y": True,
        "t": True,
        "true": True,
        "no": False,
        "n": False,
        "f": False,
        "false": False,
    }
    TYPE_CASTERS = {
        "json": json.loads,
        "integer": int,
        "float": float,
        "datetime": lambda x: arrow.get(x).datetime,
        "boolean": lambda x: BOOLEAN_LOOKUP.get(x.lower()),
    }
    reader = csv.reader(io.StringIO(data))
    raw_headers = next(reader)
    headers = []
    type_casters = {}
    for i, header in enumerate(raw_headers):
        name, *as_type = header.split("__", 1)
        headers.append(name)
        as_type = as_type[0] if as_type else None
        caster = TYPE_CASTERS.get(as_type)
        if caster:
            type_casters[name] = caster
    for row in reader:
        row_as_dict = dict(zip(headers, row))
        for name, caster in type_casters.items():
            try:
                row_as_dict[name] = caster(row_as_dict[name])
            except ValueError:
                row_as_dict[name] = None
        yield row_as_dict