from typing import List, Literal
from typing_extensions import TypedDict, NotRequired

class File(TypedDict):
    name: str
    size: int
    mime_type: NotRequired[str]
    cid: NotRequired[str]

class TransferOptions(TypedDict, total=False):
    email_me_copies: bool
    email_me_on_expire: bool
    email_upload_complete: bool
    email_download_complete: bool
    email_daily_statistics: bool
    email_report_on_closing: bool
    enable_recipient_email_download_complete: bool
    add_me_to_recipients: bool
    email_recipient_when_transfer_expires: bool
    get_a_link: bool
    hide_sender_email: bool
    redirect_url_on_complete: str
    encryption: bool
    collection: bool
    must_be_logged_in_to_download: bool
    storage_cloud_s3_bucket: bool
    web_notification_when_upload_is_complete: bool
    verify_email_to_download: bool

PartialTransfer = TypedDict("Transfer", {
    "options": NotRequired[TransferOptions],
    "expires": NotRequired[int],
    "subject": NotRequired[str],
    "message": NotRequired[str],
    # The below fields are not required when uploading to a voucher
    "recipients": NotRequired[List[str]],
    "from": NotRequired[str]
})

class Transfer(PartialTransfer):
    files: List[File]

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