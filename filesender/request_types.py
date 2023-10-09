from typing import List
from typing_extensions import TypedDict, NotRequired

class File(TypedDict):
    name: str
    size: int
    mime_type: NotRequired[str]
    cid: NotRequired[str]

Transfer = TypedDict("Transfer", {
    "files": List[File],
    "options": NotRequired[List[str]],
    "expires": NotRequired[int],
    "subject": NotRequired[str],
    "message": NotRequired[str],
    # The below fields are not required when uploading to a voucher
    "recipients": NotRequired[List[str]],
    "from": NotRequired[str]
})

class TransferUpdate(TypedDict):
    complete: NotRequired[bool]
    closed: NotRequired[bool]
    extend_expiry_date: NotRequired[bool]
    remind: NotRequired[bool]

class FileUpdate(TypedDict):
    complete: NotRequired[bool]

Guest = TypedDict("Guest", {
    "recipient": str,
    "from": str,
    "subject": NotRequired[str],
    "message": NotRequired[str],
    "options": NotRequired[List[str]],
    "transfer_options": NotRequired[List[str]],
    "expires": NotRequired[int]
})
