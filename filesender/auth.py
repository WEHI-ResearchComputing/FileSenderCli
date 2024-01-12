from dataclasses import dataclass
import hashlib
import hmac
import time
from requests import Request, Session
from urllib.parse import urlparse, urlunparse, unquote
from io import IOBase
from typing import Optional, TypeVar, Dict, cast
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

SignType = TypeVar("SignType", bound=Request)
class Auth:
    def sign(self, request: SignType, session: Session) -> SignType:
        raise Exception("No authentication was provided")


def url_without_scheme(url: str) -> str:
    """
    Returns the URL in the appropriate format for the signature calculation, namely:
    • Without a scheme
    • Without URL encoding
    • With query parameters
    """
    return unquote(urlunparse(urlparse(url)._replace(scheme="")).lstrip("/"))

@dataclass
class UserAuth(Auth):
    username: str
    api_key: str
    #: The number of seconds to delay the timestamp.
    #: See https://docs.filesender.org/filesender/v2.0/rest/#signed-request
    delay: int = 0

    def sign(self, request: SignType, session: Session) -> SignType:
        # We have to sort the params alphabetically for calculating
        # the signature
        request.params = dict(sorted({
            "remote_user": self.username,
            "timestamp": str(round(time.time() + self.delay)),
            # Manually add the session params so we can force them to be
            # alphabetical order
            **cast(Dict[str, str], session.params),
            **request.params
        }.items()))
        
        signature = hmac.new(
            key=self.api_key.encode(),
            digestmod=hashlib.sha1
        )
        signature.update(request.method.lower().encode())
        signature.update(b"&")
        signature.update(url_without_scheme(request.prepare().url).encode())

        prepared = request.prepare()
        if prepared.body is None:
            pass
        else:
            signature.update(b"&")
            if isinstance(prepared.body, str):
                signature.update(prepared.body.encode())
            elif isinstance(prepared.body, bytes):
                signature.update(prepared.body)
            elif isinstance(prepared.body, IOBase):
                while True:
                    chunk = prepared.body.read(1024)
                    if not chunk:
                        break
                    signature.update(chunk.encode())
                prepared.body.seek(0)
            else:
                raise Exception("Unknown body type")

        request.params["signature"] = signature.hexdigest()
        return request

@dataclass(unsafe_hash=True)
class GuestAuth(Auth):
    guest_token: str
    security_token: Optional[str] = None
    csrf_token: Optional[str] = None

    def prepare(self, session: Session):
        res = session.get(
            "https://filesender.aarnet.edu.au",
            params={
                "s": "upload",
                "vid": self.guest_token
            }
        )
        soup = BeautifulSoup(res.content, 'html.parser')
        self.security_token = soup.find("body").attrs["data-security-token"]
        self.csrf_token = res.cookies.get("csrfptoken")
        # We might already have the token, because we requested the server info earlier
        if self.csrf_token is None and "csrfptoken" in session.cookies:
            self.csrf_token = session.cookies._find("csrfptoken")
        if self.csrf_token is None:
            logger.warn("No CSRF token could be found!")

    def sign(self, request: SignType, session: Session) -> SignType:
        request.params["vid"] = self.guest_token
        request.headers["X-Filesender-Security-Token"] = self.security_token
        request.headers["Csrfptoken"] = self.csrf_token
        return request
