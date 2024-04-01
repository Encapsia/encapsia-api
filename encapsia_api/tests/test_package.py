import tarfile
import typing

import pytest

from encapsia_api import package


class TestMakeValidName:
    def test_empty(self):
        assert package._make_valid_name("") == ""

    def test_already_valid(self):
        assert package._make_valid_name("abc") == "abc"
        assert package._make_valid_name("aBc") == "aBc"
        assert package._make_valid_name("ABc") == "ABc"
        assert package._make_valid_name("ABc123") == "ABc123"
        assert package._make_valid_name("ABc_123") == "ABc_123"

    def test_hypens(self):
        assert package._make_valid_name("ABc-123") == "ABc_123"
        assert package._make_valid_name("-ABc-123") == "_ABc_123"
        assert package._make_valid_name("-ABc-123-") == "_ABc_123_"

    def test_spaces(self):
        assert package._make_valid_name("abc def") == "abc_def"
        assert package._make_valid_name("  abc def") == "__abc_def"
        assert package._make_valid_name("  abc def ") == "__abc_def_"

    def test_newlines(self):
        assert package._make_valid_name("abc\ndef") == "abcdef"
        assert package._make_valid_name("\n\nabc\ndef") == "abcdef"
        assert package._make_valid_name("\n\nabc\ndef\n") == "abcdef"


class TestPackageMaker:
    MANIFEST_FIELDS: typing.ClassVar[typing.Dict[str, typing.Any]] = {
        "type": {"name": "test-type", "format": "1.0", "description": "whatever"},
        "instance": {
            "name": "test instance",
            "description": "",
            "version": "1.2.3",
            "created_by": "fred",
        },
    }
    PACKAGE_FILENAME = "package-test_type-test_instance-1.2.3.tar.gz"

    def test_supported_package_formats(self):
        package.PackageMaker("1.0", self.MANIFEST_FIELDS)
        with pytest.raises(ValueError):
            package.PackageMaker("0.1", self.MANIFEST_FIELDS)
        with pytest.raises(ValueError):
            package.PackageMaker("1.1", self.MANIFEST_FIELDS)
        with pytest.raises(ValueError):
            package.PackageMaker("2.0", self.MANIFEST_FIELDS)

    def test_make_empty_package(self, tmp_path):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            filename = p.make_package(tmp_path)
            assert filename.name == self.PACKAGE_FILENAME
            with tarfile.open(filename, mode="r:gz") as tar:
                assert {m.name for m in tar.getmembers()} == {"package.toml"}

    def test_manifest_contents(self, tmp_path):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            filename = p.make_package(tmp_path)
        m = package.extract_manifest(filename)
        M = self.MANIFEST_FIELDS
        assert m["package_format"] == "1.0"
        assert sorted(m.keys()) == sorted(["package_format", "type", "instance"])
        assert sorted(m["type"].keys()) == sorted(["description", "name", "format"])
        assert sorted(m["instance"].keys()) == sorted(
            ["name", "description", "version", "created_by", "created_on"]
        )
        assert m["type"]["name"] == M["type"]["name"]
        assert m["type"]["format"] == M["type"]["format"]
        assert m["type"]["description"] == M["type"]["description"]
        assert m["instance"]["name"] == M["instance"]["name"]
        assert m["instance"]["version"] == M["instance"]["version"]
        assert m["instance"]["created_by"] == M["instance"]["created_by"]

    def test_cannot_overwrite_manifest_file(self):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:  # noqa: SIM117
            with pytest.raises(ValueError):
                p.add_file_from_string("package.toml", "whatever")

    def test_add_files_from_string(self, tmp_path):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            p.add_file_from_string("a.txt", "foo")
            p.add_file_from_string("b.txt", "bar")
            filename = p.make_package(tmp_path)
            with tarfile.open(filename, mode="r:gz") as tar:
                assert {m.name for m in tar.getmembers()} == {
                    "a.txt",
                    "b.txt",
                    "package.toml",
                }

    def test_add_files_from_directory(self, tmp_path):
        tmp_dir = tmp_path / "source"
        tmp_dir.mkdir()
        (tmp_dir / "a.txt").write_text("foo")
        (tmp_dir / "a_directory").mkdir()
        (tmp_dir / "a_directory" / "b.txt").write_text("bar")
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p:
            p.add_all_files_from_directory(tmp_dir)
            filename = p.make_package(tmp_path)
            with tarfile.open(filename, mode="r:gz") as tar:
                tar_files = {m.name for m in tar.getmembers()}
                expected_files = {
                    "a.txt",
                    "a_directory",
                    "a_directory/b.txt",
                    "package.toml",
                }
                assert tar_files == expected_files

    def test_make_same_package_fails(self, tmp_path):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p1:
            p1.add_file_from_string("a.txt", "foo")
            filename = p1.make_package(tmp_path)
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p2:
            p2.add_file_from_string("a.txt", "bar")
            with pytest.raises(FileExistsError):
                p2.make_package(tmp_path)
        dir_content = list(tmp_path.iterdir())
        assert dir_content == [filename]
        with tarfile.open(filename, mode="r:gz") as tar:
            assert {m.name for m in tar.getmembers()} == {"a.txt", "package.toml"}
            assert tar.extractfile("a.txt").read().decode() == "foo"

    def test_make_same_package_overwrites(self, tmp_path):
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p1:
            p1.add_file_from_string("a.txt", "foo")
            filename1 = p1.make_package(tmp_path)
        with package.PackageMaker("1.0", self.MANIFEST_FIELDS) as p2:
            p2.add_file_from_string("a.txt", "bar")
            filename2 = p2.make_package(tmp_path, overwrite=True)
        assert filename1 == filename2
        dir_content = list(tmp_path.iterdir())
        assert dir_content == [filename1]
        with tarfile.open(filename1, mode="r:gz") as tar:
            assert {m.name for m in tar.getmembers()} == {"a.txt", "package.toml"}
            assert tar.extractfile("a.txt").read().decode() == "bar"
