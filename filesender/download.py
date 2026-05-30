from typing import Iterable, Optional, TypedDict

from bs4 import BeautifulSoup


class DownloadFile(TypedDict):
    client_entropy: str
    encrypted: str
    encrypted_size: Optional[int]
    fileaead: str
    fileiv: str
    id: int
    key_salt: str
    key_version: Optional[int]
    mime: str
    #: filename
    name: str
    password_encoding: str
    password_hash_iterations: Optional[int]
    password_version: Optional[int]
    size: int
    transferid: int

def _opt_int(value: str) -> Optional[int]:
    return int(value) if value else None

def files_from_page(content: bytes) -> Iterable[DownloadFile]:
    """
    Yields dictionaries describing the files listed on a FileSender web page

    Params:
        content: The HTML content of the FileSender download page
    """
    for file in BeautifulSoup(content, "html.parser").find_all(
        class_="file"
    ):
        yield {
            "client_entropy": file.attrs[f"data-client-entropy"],
            "encrypted": file.attrs["data-encrypted"],
            "encrypted_size": _opt_int(file.attrs["data-encrypted-size"]),
            "fileaead": file.attrs["data-fileaead"],
            "fileiv": file.attrs["data-fileiv"],
            "id": int(file.attrs["data-id"]),
            "key_salt": file.attrs["data-key-salt"],
            "key_version": _opt_int(file.attrs["data-key-version"]),
            "mime": file.attrs["data-mime"],
            "name": file.attrs["data-name"],
            "password_encoding": file.attrs["data-password-encoding"],
            "password_hash_iterations": _opt_int(file.attrs["data-password-hash-iterations"]),
            "password_version": _opt_int(file.attrs["data-password-version"]),
            "size": int(file.attrs["data-size"]),
            "transferid": int(file.attrs["data-transferid"]),
        }
