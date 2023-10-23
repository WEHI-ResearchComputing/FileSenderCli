from dataclasses import dataclass
import hashlib
import hmac
import time
from requests import Request, Session
from urllib.parse import urlparse, urlunparse, unquote
from io import IOBase
from typing import Optional, TypeVar, Dict, cast
from bs4 import BeautifulSoup

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

    def sign(self, request: SignType, session: Session) -> SignType:
        # We have to sort the params alphabetically for calculating
        # the signature
        request.params = dict(sorted({
            "remote_user": self.username,
            "timestamp": str(round(time.time())),
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
        self.security_token = soup.find("body").attrs.get("data-security-token")
        self.csrf_token = res.cookies.get("csrfptoken")

    def sign(self, request: SignType, session: Session) -> SignType:
        request.params["vid"] = self.guest_token
        request.headers["X-Filesender-Security-Token"] = self.security_token
        request.headers["Csrfptoken"] = self.csrf_token
        return request
