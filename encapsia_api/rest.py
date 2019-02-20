import collections
import mimetypes
import tempfile
import uuid

import requests

import encapsia_api


class EncapsiaApiError(RuntimeError):
    pass


class Base:
    def __init__(self, url, token, version="v1"):
        """Initialize with server URL (e.g. https://myserver.encapsia.com)."""
        if not url.startswith("http"):
            url = "https://{}".format(url)
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
        )
        if response.status_code not in expected_codes:
            raise EncapsiaApiError(
                "{} {}\nFull response:\n{}".format(
                    response.status_code,
                    response.reason,
                    (response.content or "").strip(),
                )
            )
        if return_json:
            answer = response.json()
            if check_json_status and answer["status"] != "ok":
                raise EncapsiaApiError(response.text)
            return answer
        else:
            return response

    def get(self, *args, **kwargs):
        return self.call_api(
            "get", *args, return_json=True, check_json_status=True, **kwargs
        )

    def put(self, *args, **kwargs):
        return self.call_api(
            "put", *args, return_json=True, check_json_status=True, **kwargs
        )

    def post(self, *args, **kwargs):
        return self.call_api(
            "post", *args, return_json=True, check_json_status=True, **kwargs
        )

    def delete(self, *args, **kwargs):
        return self.call_api(
            "delete", *args, return_json=True, check_json_status=True, **kwargs
        )


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


def guess_mime_type(filename):
    mime_type = mimetypes.guess_type(filename, strict=False)[0]
    if mime_type is None:
        mime_type = "application/octet-stream"
    return mime_type


class BlobsMixin:
    def upload_file_as_blob(self, filename, mime_type=None):
        """Upload given file to blob, guessing mime_type if not given."""
        blob_id = uuid.uuid4().hex
        if mime_type is None:
            mime_type = guess_mime_type(filename)
        with open(filename, "rb") as f:
            blob_data = f.read()
            self.upload_blob_data(blob_id, mime_type, blob_data)
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
        with open(filename, "wb") as f:
            data = self.download_blob_data(blob_id)
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
            raise EncapsiaApiError(
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


class TaskMixin:
    def run_task(self, namespace, function, params, data=None):
        """Run task and return a means to poll for the result.

        Returns a function and a unique "no result yet" object. When called,
        the function will return the "no result yet" object until a reply is
        available, or raise an error, or simply return the result from the
        function.

        """
        extra_headers = {"Content-type": "application/octet-stream"} if data else None
        reply = self.post(
            ("tasks", namespace, function),
            params=params,
            data=data,
            extra_headers=extra_headers,
        )
        task_id = reply["result"]["task_id"]

        class NoResultYet:
            pass

        def get_task_result():
            reply = self.get(("tasks", namespace, task_id))
            rest_api_result = reply["result"]
            task_status = rest_api_result["status"]
            task_result = rest_api_result["result"]
            if task_status == "finished":
                return task_result
            elif task_status == "failed":
                raise EncapsiaApiError(rest_api_result)
            else:
                return NoResultYet

        return get_task_result, NoResultYet


class DbCtlMixin:
    def dbctl_action(self, name, params):
        """Request a Database control action.

        Returns a function and a unique "no reply yet" object. When called,
        the function will return the "no repy yet" object until a reply is
        available, or raise an error, or simply return the result from the
        function.

        """
        reply = self.post(("dbctl", "action", name), params=params)
        action_id = reply["result"]["action_id"]

        class NoResultYet:
            pass

        def get_result():
            reply = self.get(("dbctl", "action", action_id))
            rest_api_result = reply["result"]
            action_status = rest_api_result["status"]
            action_result = rest_api_result["result"]
            if action_status == "finished":
                return action_result
            elif action_status == "failed":
                raise EncapsiaApiError(rest_api_result)
            else:
                return NoResultYet

        return get_result, NoResultYet

    def dbctl_download_data(self, handle, filename=None):
        """Download data and return (temp) filename."""
        headers = {"Accept": "*/*", "Authorization": "Bearer {}".format(self.token)}
        url = "/".join([self.url, self.version, "dbctl/data", handle])
        response = requests.get(url, headers=headers, verify=True, stream=True)
        if response.status_code != 200:
            raise EncapsiaApiError(
                "{} {}".format(response.status_code, response.reason)
            )

        if filename is None:
            fd, filename = tempfile.mkstemp()
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        return filename

    def dbctl_upload_data(self, filename):
        """Upload data from given filename.

        Return a handle which can be used for future downloads.

        """
        with open(filename, "rb") as f:
            extra_headers = {"Content-type": "application/octet-stream"}
            response = self.post(("dbctl", "data"), data=f, extra_headers=extra_headers)
            return response["result"]["handle"]


class ConfigMixin:
    def get_all_config(self):
        """Return all server configuration."""
        return self.get("config")["result"]

    def get_config(self, key):
        """Return server configuration value for given key."""
        try:
            return self.get(("config", key))["result"][key]
        except EncapsiaApiError:
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


class SystemUserMixin:
    def add_system_user(self, description, capabilities):
        """Add system user and system role for given description and capabilities."""
        description = description.capitalize()
        encoded_description = description.lower().replace(" ", "-")
        email = f"system@{encoded_description}.encapsia.com"
        role_name = "System - " + description
        self.post(
            "roles",
            json=[
                {"name": role_name, "alias": role_name, "capabilities": capabilities}
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
        users = [
            user
            for user in self.get("users")["result"]["users"]
            if user["email"].startswith("system@")
        ]
        capabilities = {
            role["name"]: role["capabilities"]
            for role in self.get("roles")["result"]["roles"]
        }
        SystemUser = collections.namedtuple(
            "SystemUser", "email description capabilities"
        )
        for user in users:
            yield SystemUser(
                user["email"], user["last_name"], tuple(capabilities[user["role"]])
            )


class EncapsiaApi(
    Base,
    GeneralMixin,
    ReplicationMixin,
    BlobsMixin,
    LoginMixin,
    TaskMixin,
    DbCtlMixin,
    ConfigMixin,
    SystemUserMixin,
):

    """REST API access to an Encapsia server."""
