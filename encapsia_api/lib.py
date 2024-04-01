import contextlib
import mimetypes
import os
import pathlib
import shutil
import tarfile
import tempfile

import encapsia_api
from encapsia_api.resilient_request import resilient_request


def guess_mime_type(filename):
    mime_type = mimetypes.guess_type(str(filename), strict=False)[0]
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
def download_to_file(url, token, target_file=None, cleanup=True):
    """Context manager for downloading a fixed file to a target_file."""
    if target_file is None:
        filename = pathlib.Path(tempfile.mkstemp()[1])
    else:
        filename = pathlib.Path(target_file)
    try:
        headers = {"Accept": "*/*", "Authorization": f"Bearer {token}"}
        response = resilient_request(
            "get", url, headers=headers, verify=True, stream=True
        )
        if response.status_code != 200:
            raise encapsia_api.EncapsiaApiError(
                f"{response.status_code} {response.reason}"
            )
        stream_response_to_file(response, filename)
        yield filename
    finally:
        if cleanup:
            filename.unlink()


@contextlib.contextmanager
def make_temp_dir_path(cleanup=True):
    """Context manager for creating a temporary directory."""
    directory = pathlib.Path(tempfile.mkdtemp())
    try:
        yield directory
    finally:
        if cleanup:
            shutil.rmtree(directory)


@contextlib.contextmanager
def make_temp_file_path(cleanup=True, dir=None):
    fd, name = tempfile.mkstemp(dir=dir)
    os.close(fd)
    path = pathlib.Path(name)
    try:
        yield path
    finally:
        if cleanup:
            path.unlink(missing_ok=True)


@contextlib.contextmanager
def untar_to_dir(filename, target_dir=None, cleanup=True):
    """Context manager for creating a directory with contents of tar.gz.

    If target_dir is None then a temporary directory is created.

    """
    if target_dir:
        try:
            tar = tarfile.open(filename)
            tar.extractall(target_dir)  # noqa: S202
            tar.close()
            yield target_dir
        finally:
            if cleanup:
                shutil.rmtree(target_dir)
    else:
        with make_temp_dir_path(cleanup=cleanup) as directory:
            tar = tarfile.open(filename)
            tar.extractall(directory)  # noqa: S202
            tar.close()
            yield directory
