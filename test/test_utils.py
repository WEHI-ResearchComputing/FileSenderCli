from filesender.api import iter_files, _file_key
from filesender.response_types import _FileWithUid, _FileWithPuid
from filesender.download import files_from_page
from pathlib import Path
import tempfile
import pytest


# Minimal file dicts matching the structure of the real API response

FILE_WITH_UID: _FileWithUid = {
    "id": 28000001,
    "transfer_id": 3500001,
    "uid": "abc123def456",
    "name": "example.txt",
    "size": 1024,
    "sha1": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
}

FILE_WITH_PUID: _FileWithPuid = {
    "id": 28622026,
    "transfer_id": 3573766,
    "puid": "91dc452a-7d5c-4e34-9bee-6bc44fa5e012",
    "name": "final_train.h5",
    "size": "5243079740",  # AARNet server returns size as a string
    "sha1": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
}

# Minimal HTML matching the structure of the FileSender download page

DOWNLOAD_PAGE_ENCRYPTED = b"""
<html><body>
<div class="file"
    data-id="1"
    data-transfer-id="1"
    data-name="secret.txt"
    data-size="1024"
    data-mime="text/plain"
    data-encrypted="1"
    data-encrypted-size="1040"
    data-fileiv="aabbccdd"
    data-fileaead="eeff0011"
    data-key-version="1"
    data-key-salt="saltsalt"
    data-client-entropy="entropydata"
    data-password-version="1"
    data-password-encoding="base64"
    data-password-hash-iterations="10000"
    data-transferid="1">
</div>
</body></html>
"""

DOWNLOAD_PAGE_UNENCRYPTED = b"""
<html><body>
<div class="file"
    data-id="2"
    data-transfer-id="2"
    data-name="plain.txt"
    data-size="2048"
    data-mime="text/plain"
    data-encrypted="0"
    data-encrypted-size=""
    data-fileiv=""
    data-fileaead=""
    data-key-version=""
    data-key-salt=""
    data-client-entropy=""
    data-password-version=""
    data-password-encoding=""
    data-password-hash-iterations=""
    data-transferid="2">
</div>
</body></html>
"""


def test_file_key_uid():
    assert _file_key(FILE_WITH_UID) == "abc123def456"


def test_file_key_puid():
    assert _file_key(FILE_WITH_PUID) == "91dc452a-7d5c-4e34-9bee-6bc44fa5e012"


def test_file_key_neither():
    file: _FileWithUid = {
        "id": 1,
        "transfer_id": 1,
        "uid": "x",
        "name": "test.txt",
        "size": 0,
        "sha1": "",
    }
    # Strip the uid at runtime to simulate a response with neither field
    d = dict(file)
    del d["uid"]
    with pytest.raises(Exception, match="neither 'uid' nor 'puid'"):
        _file_key(d)  # type: ignore[arg-type]


def test_files_from_page_encrypted():
    (file,) = files_from_page(DOWNLOAD_PAGE_ENCRYPTED)
    assert file["name"] == "secret.txt"
    assert file["size"] == 1024
    assert file["encrypted_size"] == 1040
    assert file["key_version"] == 1
    assert file["password_hash_iterations"] == 10000


def test_files_from_page_unencrypted():
    (file,) = files_from_page(DOWNLOAD_PAGE_UNENCRYPTED)
    assert file["name"] == "plain.txt"
    assert file["size"] == 2048
    assert file["encrypted_size"] is None
    assert file["key_version"] is None
    assert file["password_hash_iterations"] is None

def test_iter_files():
    with tempfile.TemporaryDirectory() as _tempdir:
        tempdir = Path(_tempdir)
        top_level_file = tempdir / "top_level_file"
        top_level_file.touch()

        top_level_dir = (tempdir / "top_level_dir")
        top_level_dir.mkdir()

        nested_file = top_level_dir / "nested_file.txt"
        nested_file.touch()

        nested_dir = top_level_dir / "nested_dir/"
        nested_dir.mkdir()

        doubly_nested_file = nested_dir / "doubly_nested_file.csv"
        doubly_nested_file.touch()

        assert set(iter_files([top_level_dir, top_level_file])) == {("top_level_file", top_level_file), ("top_level_dir/nested_file.txt", nested_file), ("top_level_dir/nested_dir/doubly_nested_file.csv", doubly_nested_file)}
