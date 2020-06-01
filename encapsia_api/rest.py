import collections
import csv
import json
import pathlib
import subprocess
import sys
import time
import uuid

import arrow
import requests

import encapsia_api
from encapsia_api.lib import (
    download_to_file,
    guess_mime_type,
    guess_upload_content_type,
    stream_response_to_file,
    untar_to_dir,
)

__all__ = ["EncapsiaApi", "EncapsiaApiTimeoutError", "FileDownloadResponse"]


class EncapsiaApiTimeoutError(encapsia_api.EncapsiaApiError):
    pass


class Base:
    def __init__(self, url, token, version="v1"):
        """Initialize with server URL (e.g. https://myserver.encapsia.com)."""
        if not url.startswith("http"):
            url = f"https://{url}"
        self.url = url.rstrip("/")
        self.token = token
        self.version = version

    def __str__(self):
        return self.url

    def call_api(
        self,
        method,
        path_segments,
        data=None,
        json=None,
        return_json=False,
        check_json_status=False,
        extra_headers=None,
        expected_codes=(200, 201),
        params=None,
        stream=False,
    ):
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(self.token),
            "User-Agent": f"encapsia-api/{encapsia_api.__version__}",
        }
        if json:
            headers["Content-type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        if path_segments:
            segments = [self.url, self.version]
            if isinstance(path_segments, str):
                segments.append(path_segments.lstrip("/"))
            else:
                segments.extend([s.lstrip("/") for s in path_segments])
        else:
            segments = [self.url]
        url = "/".join(segments)
        response = requests.request(
            method,
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            verify=True,
            allow_redirects=False,
            stream=stream,
        )
        if response.status_code not in expected_codes:
            raise encapsia_api.EncapsiaApiError(
                "{} {}\nFull response:\n{}".format(
                    response.status_code,
                    response.reason,
                    (response.content or "").strip(),
                )
            )
        if not stream and return_json:
            answer = response.json()
            if check_json_status and answer["status"] != "ok":
                raise encapsia_api.EncapsiaApiError(response.text)
            return answer
        else:
            return response

    def get(self, *args, **kwargs):
        kwargs.setdefault("return_json", True)
        kwargs.setdefault("check_json_status", True)
        return self.call_api("get", *args, **kwargs)

    def put(self, *args, **kwargs):
        kwargs.setdefault("return_json", True)
        kwargs.setdefault("check_json_status", True)
        return self.call_api("put", *args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs.setdefault("return_json", True)
        kwargs.setdefault("check_json_status", True)
        return self.call_api("post", *args, **kwargs)

    def delete(self, *args, **kwargs):
        kwargs.setdefault("return_json", True)
        kwargs.setdefault("check_json_status", True)
        return self.call_api("delete", *args, **kwargs)


class GeneralMixin:
    def whoami(self):
        return self.get("whoami")["result"]


class ReplicationMixin:
    def get_hwm(self):
        answer = self.post(
            ("sync", "out"), json=[], params=dict(all_zones=True, limit=0)
        )
        return answer["result"]["hwm"]

    def get_assertions(self, hwm, blocksize):
        answer = self.post(
            ("sync", "out"), json=hwm, params=dict(all_zones=True, limit=blocksize)
        )
        assertions = answer["result"]["assertions"]
        hwm = answer["result"]["hwm"]
        return assertions, hwm

    def post_assertions(self, assertions):
        self.post(("sync", "in"), json=assertions)


class BlobsMixin:
    def upload_file_as_blob(self, filename, mime_type=None):
        """Upload given file to blob, guessing mime_type if not given."""
        filename = pathlib.Path(filename)
        blob_id = uuid.uuid4().hex
        if mime_type is None:
            mime_type = guess_mime_type(filename)
        with filename.open("rb") as f:
            blob_data = f.read()
            self.upload_blob_data(
                blob_id, mime_type, blob_data
            )  # TODO be memory efficienct
            return blob_id

    def upload_blob_data(self, blob_id, mime_type, blob_data):
        """Upload blob data."""
        extra_headers = {"Content-type": mime_type}
        self.call_api(
            "put",
            ("blobs", blob_id),
            data=blob_data,
            extra_headers=extra_headers,
            return_json=True,
            check_json_status=True,
        )

    def download_blob_to_file(self, blob_id, filename):
        """Download blob to given filename."""
        filename = pathlib.Path(filename)
        with filename.open("wb") as f:
            data = self.download_blob_data(
                blob_id
            )  # TODO stream it to make it memory efficient
            if data:
                f.write(data)

    def download_blob_data(self, blob_id):
        """Download blob data for given blob_id."""
        extra_headers = {"Accept": "*/*"}
        response = self.call_api(
            "get",
            ("blobs", blob_id),
            extra_headers=extra_headers,
            expected_codes=(200, 302, 404),
        )
        if response.status_code == 200:
            return response.content
        elif response.status_code in (302, 404):
            return None
        else:
            raise encapsia_api.EncapsiaApiError(
                "Unable to download blob {}: {}".format(blob_id, response.status_code)
            )

    def get_blobs(self):
        return self.get("blobs")["result"]["blobs"]

    def tag_blobs(self, blob_ids, tag):
        post_data = [{"blob_id": blob_id, "tag": tag} for blob_id in blob_ids]
        self.post("blobtags", post_data)

    def delete_blobtag(self, blob_id, tag):
        self.delete(("blobtags", blob_id, tag))

    def get_blob_ids_with_tag(self, tag):
        return self.get(("blobtags", "", tag))["result"]["blob_ids"]

    def trim_blobtags(self, blob_ids, tag):
        """Ensure only the given blobs have given tag."""
        server_blob_ids = self.get_blob_ids_with_tag(tag)
        unwanted = set(server_blob_ids) - set(blob_ids)
        for blob_id in unwanted:
            print("Untagging blob {} for tag {}".format(blob_id, tag))
            self.delete_blobtag(blob_id, tag)


class LoginMixin:
    def login_transfer(self, user, lifespan=600):
        data = {"lifespan": lifespan}
        answer = self.post(("login", "transfer", user), json=data)
        return answer["result"]["token"]

    def login_federate(self, origin_server, origin_token, federated_group):
        data = {
            "origin_server": origin_server,
            "origin_token": origin_token,
            "group": federated_group,
        }
        answer = self.post(("login", "federate"), json=data)
        return answer["result"]["token"]

    def login_again(self, capabilities=None, lifespan=None):
        data = {}
        if capabilities:
            data["capabilities"] = capabilities
        if lifespan:
            data["lifespan"] = lifespan
        answer = self.post(("login", "again"), json=data)
        return answer["result"]["token"]


class FileDownloadResponse:
    """Object returned from a task or view when responding with a downloaded file."""

    def __init__(self, filename, mime_type):
        self.filename = filename
        self.mime_type = mime_type


class Boolean:

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

    def from_str(self, value):
        try:
            return self.BOOLEAN_LOOKUP[value.lower()]
        except KeyError:
            raise ValueError(f"Cannot convert {value} to boolean.")


class CsvResponse:
    """Iterable returned from a task or view when responding with non-downloaded CSV."""

    TYPE_CASTERS = {
        "json": json.loads,
        "integer": int,
        "float": float,
        "datetime": lambda x: arrow.get(x).datetime,
        "boolean": Boolean().from_str,
    }

    def __init__(self, line_iterable):
        self.reader = csv.reader(line_iterable)
        self.headers, self.type_casters = self._parse_headers()

    def _parse_headers(self):
        raw_headers = next(self.reader)
        headers = []
        type_casters = {}
        for i, header in enumerate(raw_headers):
            name, *as_type = header.split("__", 1)
            headers.append(name)
            as_type = as_type[0] if as_type else None
            caster = self.TYPE_CASTERS.get(as_type)
            if caster:
                type_casters[name] = caster
        return headers, type_casters

    def __iter__(self):
        for row in self.reader:
            row_as_dict = dict(zip(self.headers, row))
            for name, caster in self.type_casters.items():
                try:
                    row_as_dict[name] = caster(row_as_dict[name])
                except ValueError:
                    row_as_dict[name] = None
            yield row_as_dict


class TaskMixin:
    def run_task(self, namespace, function, params, upload=None, download=None):
        """Run task and return a means to poll for the result.

        If provided, `upload` should be str, bytes, or file-like object. Note that
        a file-like object can be large because it is streamed.

        Returns a `get_task_result` function and a unique `NoResultYet` object.

        When called, the `get_task_result` function will return the `NoResultYet`
        object until a reply is available. Once a reply is available, the function will
        either return the response directly as unicode text or stream it to a file provided
        by the `download` argument if provided. In that case (and only in that case), a
        `FileDownloadResponse` response object is returned to indicate success and
        provide the `mime_type`.

        Any errors result in an exception being raised.

        """
        content_type = guess_upload_content_type(upload)
        reply = self.post(
            ("tasks", namespace, function),
            params=params,
            extra_headers={"Content-type": content_type} if content_type else None,
            data=upload,
        )
        task_id = reply["result"]["task_id"]

        class NoResultYet:
            pass

        def get_task_result():
            with self.call_api(
                "get", ("tasks", namespace, task_id), stream=True
            ) as response:
                if response.headers.get("Content-type") == "application/json":
                    reply = response.json()
                    if reply.get("status") != "ok":
                        raise encapsia_api.EncapsiaApiError(response.text)
                    rest_api_result = reply["result"]
                    task_status = rest_api_result["status"]
                    task_result = rest_api_result["result"]
                    if task_status == "finished":
                        if download:
                            filename = pathlib.Path(download)
                            with filename.open("wt") as f:
                                json.dump(task_result, f, indent=4)
                            return FileDownloadResponse(filename, "application/json")
                        else:
                            return task_result
                    elif task_status == "failed":
                        raise encapsia_api.EncapsiaApiFailedTaskError(
                            "Failed Task. See Exception payload attribute.",
                            payload=rest_api_result,
                        )
                    else:
                        return NoResultYet
                else:
                    # Stream the response directly to the given file.
                    # Note we don't care whether this is JSON, CSV, or some other type.
                    if download:
                        filename = pathlib.Path(download)
                        stream_response_to_file(response, filename)
                        return FileDownloadResponse(
                            filename, response.headers.get("Content-type")
                        )
                    else:
                        return response.text

        return get_task_result, NoResultYet

    def run_task_and_poll(self, *args, every=0.2, max_tries=100, **kwargs):
        """Poll `run_task` until result obtained or max number of tries exceeded."""
        poll, NoTaskResultYet = self.run_task(*args, **kwargs)
        result = poll()
        n = 0
        while n < max_tries and result is NoTaskResultYet:
            time.sleep(every)
            result = poll()
            n += 1
        if result is NoTaskResultYet:
            raise EncapsiaApiTimeoutError(
                f"Task didn't respond after {every * max_tries} seconds."
            )
        return result

    def run_plugins_task(self, name, params, data=None):
        """Convenience function for calling pluginsmanager tasks."""
        reply = self.run_task_and_poll(
            "pluginsmanager", "icepluginsmanager.{}".format(name), params, upload=data
        )
        if reply["status"] == "ok":
            return reply["output"].strip()
        else:
            raise RuntimeError(str(reply))


class JobMixin:
    def run_job(self, namespace, function, params, upload=None, download=None):
        """Run job and return a means to poll for the result.

        If provided, `upload` should be str, bytes, or file-like object. Note that
        a file-like object can be large because it is streamed.

        Returns a `get_job_result` function and a unique `NoResultYet` object.

        When called, the `get_job_result` function will return the `NoResultYet`
        object until a reply is available. Once a reply is available, the function will
        either return the response directly or stream it to a file provided by the
        `download` argument if provided. In that case (and only in that case), a
        `FileDownloadResponse` response object is returned to indicate success and
        provide the `mime_type`.

        Any errors result in an exception being raised.

        """
        content_type = guess_upload_content_type(upload)
        reply = self.post(
            ("jobs", namespace, function),
            params=params,
            extra_headers={"Content-type": content_type} if content_type else None,
            data=upload,
        )
        task_id = reply["result"]["task_id"]
        job_id = reply["result"]["job_id"]

        class NoResultYet:
            pass

        def get_job_result():
            with self.call_api("get", ("tasks", namespace, task_id)) as response:
                reply = response.json()
                if reply.get("status") != "ok":
                    raise encapsia_api.EncapsiaApiError(response.text)
                rest_api_result = reply["result"]
                task_status = rest_api_result["status"]
                if task_status == "finished":
                    reply = self.get(("jobs", namespace, job_id))
                    joblog = reply["result"]["logs"][0]
                    assert joblog["status"] == "success"
                    result = joblog["output"]
                    if download:
                        filename = pathlib.Path(download)
                        with filename.open("wt") as f:
                            json.dump(result, f, indent=4)
                        return FileDownloadResponse(filename, "application/json")
                    else:
                        return result
                elif task_status == "failed":
                    raise encapsia_api.EncapsiaApiFailedTaskError(
                        "Failed Task behind the Job. See Exception payload attribute.",
                        payload=rest_api_result,
                    )
                else:
                    return NoResultYet

        return get_job_result, NoResultYet


class ViewMixin:
    def run_view(
        self,
        namespace,
        function,
        view_arguments=[],
        view_options={},
        use_post=False,
        upload=None,
        download=None,
        typed_csv=False,
    ):
        """Run a view function and return its result.

        The `view_arguments` will become path segments in the URL.
        The `view_options` will become query string arguments in the URL.

        For views which modify the database in some way (e.g. create a temporary table),
        use `use_post=True`.

        If provided, `upload` should be str, bytes, or file-like object. Note that
        a file-like object can be large because it is streamed.

        Either returns the response directly or streams to a file provided by the
        `download` argument if provided. In that case (and only in that case), a
        `FileDownloadResponse` response object is returned to indicate success and
        provide the `mime_type`.

        If no `download` is requested then decoding is performed if the content-type is
        either CSV or JSON. JSON is returned decoded as Python objects.
        In the case of CSV, if `typed_csv` is False then the raw text is returned unparsed. If
        `typed_csv` is True then an iterable CsvResponse object is returned. This is memory
        efficient, and tries to coerce the data into types according to a column
        naming convention of the form <name>__<type>. Supported types are
        integer, float, boolean, datetime, and json. Otherwise, if neither JSON or CSV
        then the response is unicode text.

        Any errors result in an exception being raised.

        """
        content_type = guess_upload_content_type(upload)
        response = self.call_api(
            "POST" if use_post else "GET",
            ("views", namespace, function) + tuple(view_arguments),
            params=view_options,
            extra_headers={"Content-type": content_type} if content_type else None,
            data=upload,
            stream=True,
        )
        if download:
            filename = pathlib.Path(download)
            stream_response_to_file(response, filename)
            return FileDownloadResponse(filename, response.headers.get("Content-type"))
        else:
            if response.headers.get("Content-type") == "application/json":
                return response.json()
            elif typed_csv and response.headers.get("Content-type") == "text/csv":
                return CsvResponse(response.iter_lines(decode_unicode=True))
            else:
                return response.text


class DbCtlMixin:
    def dbctl_action(self, name, params):
        """Request a Database control action.

        Returns a function and a unique "no reply yet" object. When called,
        the function will return the "no reply yet" object until a reply is
        available, or raise an error, or simply return the result from the
        function.

        """
        reply = self.post(("dbctl", "action", name), params=params)
        action_id = reply["result"]["action_id"]

        class NoResultYet:
            pass

        def get_result():
            reply = self.get(("dbctl", "action", name, action_id))
            rest_api_result = reply["result"]
            action_status = rest_api_result["status"]
            action_result = rest_api_result["result"]
            if action_status == "finished":
                return action_result
            elif action_status == "failed":
                raise encapsia_api.EncapsiaApiFailedTaskError(
                    "Failed dbctl task. See Exception payload attribute.",
                    payload=rest_api_result,
                )
            else:
                return NoResultYet

        return get_result, NoResultYet

    def dbctl_download_data(self, handle, filename=None):
        """Download data and return (temp) filename."""
        url = "/".join([self.url, self.version, "dbctl/data", handle])
        with download_to_file(url, self.token, cleanup=False) as filename:
            return filename

    def dbctl_upload_data(self, filename):
        """Upload data from given filename.

        Return a handle which can be used for future downloads.

        """
        filename = pathlib.Path(filename)
        with filename.open("rb") as f:
            extra_headers = {"Content-type": "application/octet-stream"}
            response = self.post(("dbctl", "data"), data=f, extra_headers=extra_headers)
            return response["result"]["handle"]


class MiscMixin:
    def download_file(self, url_path, target=None, untargz=False):
        """Download static file to target file/dir (if untargz is True).

        If target is None then a temporary file/dir is used.

        """
        url = "/".join([self.url, url_path])
        if untargz:
            with download_to_file(url, self.token) as tmp_filename:
                with untar_to_dir(
                    tmp_filename, target=target, cleanup=False
                ) as directory:
                    return directory
        else:
            with download_to_file(
                url, self.token, target=target, cleanup=False
            ) as filename:
                return filename

    def pip_install_from_plugin(self, namespace, wheelhouse="python/wheelhouse.tar.gz"):
        """Download and install Python packages published by given plugin/namespace.

        The output from `pip install` is sent to stdout/err.

        """
        url = "/".join([self.url, namespace, wheelhouse])
        with download_to_file(url, self.token) as tmp_filename:
            with untar_to_dir(tmp_filename) as tmp_dir:
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "--find-links",
                        tmp_dir,
                        "--requirement",
                        tmp_dir / "requirements.txt",
                    ]
                )


class ConfigMixin:
    def get_all_config(self):
        """Return all server configuration."""
        return self.get("config")["result"]

    def get_config(self, key):
        """Return server configuration value for given key."""
        try:
            return self.get(("config", key))["result"][key]
        except encapsia_api.EncapsiaApiError:
            raise KeyError(key)

    def set_config(self, key, value):
        """Set server configuration value for given key."""
        self.put(("config", key), json=value)

    def set_config_multi(self, data):
        """Set multiple server configuration values from JSON dictionary."""
        self.post("config", json=data)

    def delete_config(self, key):
        """Delete server configuration value associated with given key."""
        self.delete(("config", key))


class UserMixin:
    def delete_user(self, email):
        self.delete(("users", email))

    def get_all_users(self):
        """Return raw json of all users."""
        return self.get("users")["result"]["users"]

    def get_all_roles(self):
        """Return raw json of all roles."""
        return self.get("roles")["result"]["roles"]


class SystemUserMixin:
    def make_system_user_email_from_description(self, description):
        """Construct and return system user email from given description."""
        encoded_description = description.lower().replace(" ", "-")
        return f"system@{encoded_description}.encapsia.com"

    def make_system_user_role_name_from_description(self, description):
        """Construct and return system user role name from given description."""
        return "System - " + description.capitalize()

    def add_system_user(self, description, capabilities, force=False):
        """Add system user and system role for given description and capabilities."""
        description = description.capitalize()
        email = self.make_system_user_email_from_description(description)
        role_name = self.make_system_user_role_name_from_description(description)
        should_add = force or not any(
            (
                email == system_user.email
                and description == system_user.description
                and set(capabilities) == set(system_user.capabilities)
            )
            for system_user in self.get_system_users()
        )
        if should_add:
            self.post(
                "roles",
                json=[
                    {
                        "name": role_name,
                        "alias": role_name,
                        "capabilities": capabilities,
                    }
                ],
            )
            self.post(
                "users",
                json=[
                    {
                        "email": email,
                        "first_name": "System",
                        "last_name": description,
                        "role": role_name,
                        "enabled": True,
                        "is_site_user": False,
                    }
                ],
            )

    def get_system_users(self):
        """Yield namedtuples of system users."""
        users = [
            user for user in self.get_all_users() if user["email"].startswith("system@")
        ]
        capabilities = {
            role["name"]: role["capabilities"] for role in self.get_all_roles()
        }
        SystemUser = collections.namedtuple(
            "SystemUser", "email description capabilities"
        )
        for user in users:
            yield SystemUser(
                user["email"], user["last_name"], tuple(capabilities[user["role"]])
            )

    def get_system_user_by_description(self, description):
        """Return namedtuple of system user with given description if found."""
        description = description.capitalize()
        for user in self.get_system_users():
            if user.description == description:
                return user


class SuperUserMixin:
    def add_super_user(self, email, first_name, last_name):
        """Add a superuser and superuser role."""
        self.post(
            "roles",
            json=[
                {
                    "name": "Superuser",
                    "alias": "Superuser",
                    "capabilities": ["superuser"],
                }
            ],
        )
        self.post(
            "users",
            json=[
                {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": "Superuser",
                    "enabled": True,
                    "is_site_user": False,
                }
            ],
        )

    def get_super_users(self):
        """Yield namedtuples of superusers."""
        SuperUser = collections.namedtuple("SuperUser", "email first_name last_name")
        for user in self.get_all_users():
            if user["role"] == "Superuser":
                yield SuperUser(user["email"], user["first_name"], user["last_name"])


class EncapsiaApi(
    Base,
    GeneralMixin,
    ReplicationMixin,
    BlobsMixin,
    LoginMixin,
    TaskMixin,
    JobMixin,
    ViewMixin,
    DbCtlMixin,
    MiscMixin,
    ConfigMixin,
    UserMixin,
    SystemUserMixin,
    SuperUserMixin,
):

    """REST API access to an Encapsia server."""
