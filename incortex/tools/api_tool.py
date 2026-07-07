"""ApiTool — HTTP GET, the external-reach ability (Design_Doc §18.3).

Level 3 (external API action): above the default permission ceiling, so
it stays locked until configuration deliberately raises the ceiling. Only
http/https URLs, bounded response size, injectable opener for tests.
"""

import urllib.request

from incortex.tools.base_tool import BaseTool

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_BYTES = 65_536


class ApiTool(BaseTool):
    name = "api_get"
    description = "fetch a URL over HTTP GET"
    permission_level = 3  # external API action (Design_Doc §12.9)
    harm_probability = 0.2
    impact = 0.4

    def __init__(self, opener=urllib.request.urlopen,
                 timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                 max_bytes=DEFAULT_MAX_BYTES):
        self._opener = opener
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes

    def validate(self, request):
        super().validate(request)
        url = request.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError(f"{self.name}: 'url' must start with http:// or https://")

    def _execute(self, request):
        with self._opener(request["url"], timeout=self._timeout) as response:
            body = response.read(self._max_bytes + 1)
        if len(body) > self._max_bytes:
            raise ValueError(f"response too large (over {self._max_bytes} bytes)")
        return {"url": request["url"],
                "body": body.decode("utf-8", errors="replace"),
                "length": len(body)}
