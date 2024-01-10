from dataclasses import dataclass
import hashlib
import hmac
import time
from httpx import Request, QueryParams, AsyncClient
from urllib.parse import urlparse, urlunparse, unquote
from typing import Optional, TypeVar
from bs4 import BeautifulSoup
from collections.abc import Iterable

SignType = TypeVar("SignType", bound=Request)
class Auth:
    def sign(self, request: SignType, client: AsyncClient) -> SignType:
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

    def sign(self, request: SignType, client: AsyncClient) -> SignType:
        # Merge in some additional parameters, and then sort by key
        # so the params are in alphabetical order as required
        params = QueryParams(tuple(sorted(request.url.params.merge({
                "remote_user": self.username,
                "timestamp": str(round(time.time() + self.delay)),
                # Manually add the session params so we can force them to be
                # alphabetical order
                # **cast(Dict[str, str], session.params),
                # **request.params
            }).items())))
        request.url = request.url.copy_with(params=params)
        
        signature = hmac.new(
            key=self.api_key.encode(),
            digestmod=hashlib.sha1
        )
        signature.update(request.method.lower().encode())
        signature.update(b"&")
        signature.update(url_without_scheme(str(request.url)).encode())

        if isinstance(request.stream, Iterable):
            for i, chunk in enumerate(request.stream):
                if i == 0:
                    signature.update(b"&")
                signature.update(chunk)
        else:
            raise Exception("?")

        request.url = request.url.copy_add_param("signature", signature.hexdigest())
        return request

@dataclass(unsafe_hash=True)
class GuestAuth(Auth):
    guest_token: str
    security_token: Optional[str] = None
    csrf_token: Optional[str] = None

    async def prepare(self, client: AsyncClient):
        res = await client.get(
            "https://filesender.aarnet.edu.au",
            params={
                "s": "upload",
                "vid": self.guest_token
            }
        )
        soup = BeautifulSoup(res.content, 'html.parser')
        self.security_token = soup.find("body").attrs.get("data-security-token")
        self.csrf_token = res.cookies.get("csrfptoken")

    def sign(self, request: SignType, client: AsyncClient) -> SignType:
        request.url = request.url.copy_add_param("vid", self.guest_token)
        if self.security_token is None or self.csrf_token is None:
            raise Exception(".prepare() must be called on the GuestAuth before it is used to sign requests")
        request.headers["X-Filesender-Security-Token"] = self.security_token
        # request.headers["Csrfptoken"] = self.csrf_token
        return request
