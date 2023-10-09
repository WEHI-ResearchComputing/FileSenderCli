from typing import List
from typing_extensions import TypedDict

class File(TypedDict):
    id: int
    transfer_id: int
    uid: str
    name: str
    size: int
    sha1: str

class Date(TypedDict):
    raw: int
    formatted: str

class TrackingError(TypedDict):
    type: str
    date: Date
    details: str

class Recipient(TypedDict):
    id: int
    transfer_id: int
    token: str
    email: str
    created: Date
    last_activity: Date
    options: None
    download_url: str
    errors: List[TrackingError]

class Transfer(TypedDict):
    id: int
    user_id: str
    user_email: str
    subject: str
    message: str
    created: List[Date]
    expires: Date
    expiry_date_extension: int
    options: List[str]
    files: List[File]
    recipients: List[Recipient]
    roundtriptoken: str
    salt: str

class Guest(TypedDict):
    id: int
    user_id: str
    user_email: str
    email: str
    token: str
    transfer_count: int
    subject: str
    message: str
    options: List[str]
    transfer_options: List[str]
    created: Date
    expires: Date
    errors: List[TrackingError]

class Author(TypedDict):
    type: str
    id: str
    ip: str
    email: str

class Target(TypedDict):
    type: str
    id: str
    name: str
    size: int
    email: str

class AuditLog(TypedDict):
    date: Date
    event: str
    author: Author
    target: Target
