import contextlib
import mimetypes
import pathlib
import shutil
import tarfile
import tempfile

import requests

import encapsia_api


def guess_mime_type(filename):
    mime_type = mimetypes.guess_type(filename, strict=False)[0]
    if mime_type is None:
        mime_type = "application/octet-stream"
    return mime_type


def guess_upload_content_type(upload):
    if upload:
        if isinstance(upload, str):
            return "text/plain; charset=utf-8"
        elif hasattr(upload, "name"):
            return guess_mime_type(upload.name)
        return "application/octet-stream"
    return None


def stream_response_to_file(response, filename):
    # NB Using shutil.copyfileobj is an attractive option, but does not
    # decode the gzip and deflate transfer-encodings...
    with filename.open("wb") as f:
        for chunk in response.iter_content(chunk_size=None):
            f.write(chunk)


@contextlib.contextmanager
def download_to_temp_file(url, token):
    headers = {"Accept": "*/*", "Authorization": "Bearer {}".format(token)}
    response = requests.get(url, headers=headers, verify=True, stream=True)
    if response.status_code != 200:
        raise encapsia_api.EncapsiaApiError(
            "{} {}".format(response.status_code, response.reason)
        )
    _, filename = tempfile.mkstemp()
    filename = pathlib.Path(filename)
    try:
        stream_response_to_file(response, filename)
        yield filename
    finally:
        shutil.rmtree(filename)


@contextlib.contextmanager
def temp_dir():
    """Context manager for creating a temporary directory.

    Cleans up afterwards.

    """
    directory = pathlib.Path(tempfile.mkdtemp())
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


@contextlib.contextmanager
def untar_to_temp_dir(filename):
    """Context manager for creating a temp directory with contents of tar.gz.

    Yields the name of the temp directory (which is cleaned up afterwards).

    """
    with temp_dir() as directory:
        tar = tarfile.open(filename)
        tar.extractall(directory)
        tar.close()
        yield directory
