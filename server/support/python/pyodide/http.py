"""Stand-in for Pyodide's pyfetch: the lessons were written for in-browser Python; this runs them locally."""
import asyncio
import json as _json
import urllib.error
import urllib.request


class FetchResponse:
    def __init__(self, url, status, reason, headers, body):
        self.url, self.status, self.status_text = url, status, reason
        self.headers = dict(headers or {})
        self.ok = 200 <= status < 300
        self._body = body

    async def bytes(self):
        return self._body

    async def string(self):
        return self._body.decode()

    text = string

    async def json(self):
        return _json.loads(self._body)


def _fetch(url, method, headers, body):
    data = body.encode() if isinstance(body, str) else body
    headers = {'User-Agent': 'nagare', **(headers or {})}  # the lessons' API rejects Python's default agent
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return FetchResponse(url, r.status, r.reason, r.headers, r.read())
    except urllib.error.HTTPError as e:  # like fetch(): an HTTP error status is still a response
        return FetchResponse(url, e.code, e.reason, e.headers, e.read())


async def pyfetch(url, method="GET", headers=None, body=None, **kwargs):
    return await asyncio.to_thread(_fetch, url, method, headers, body)
