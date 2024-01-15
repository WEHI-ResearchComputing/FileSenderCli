from typing import List
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

PartialTransfer = TypedDict("PartialTransfer", {
    "options": NotRequired[TransferOptions],
    "expires": NotRequired[int],
    "subject": NotRequired[str],
    "message": NotRequired[str],
    # The below fields are not required when uploading to a voucher
    "recipients": NotRequired[List[str]],
    # We need to use the expression syntax for TypedDict because `from` is a Python keyword
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

class GuestOptions(TypedDict, total=False):
    valid_only_one_time: bool
    can_only_send_to_me: bool
    email_upload_started: bool
    email_upload_page_access: bool
    email_guest_created: bool
    email_guest_created_receipt: bool
    email_guest_expired: bool

class GuestAllOptions(TypedDict):
    guest: NotRequired[GuestOptions]
    transfer: NotRequired[TransferOptions]

Guest = TypedDict("Guest", {
    "recipient": str,
    "from": str,
    "subject": NotRequired[str],
    "message": NotRequired[str],
    # See https://github.com/filesender/filesender/issues/1772
    "options": NotRequired[GuestAllOptions],
    "expires": NotRequired[int]
})
