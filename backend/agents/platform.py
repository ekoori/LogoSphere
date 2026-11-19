"""The LogoSphere API as one persona sees it (Authorization: Bearer).

Personas act only through the API, so every platform rule applies to them as
to any member. The director talks to the backend on the same host.
"""
import json
import urllib.error
import urllib.request
import uuid

from agents import config


class PlatformError(Exception):
    def __init__(self, status, message):
        super().__init__(f'{status}: {message}')
        self.status = status
        self.message = message


class Platform:
    def __init__(self, token, base=None, timeout=30):
        self.token = token
        self.base = (base or config.API).rstrip('/')
        self.timeout = timeout

    def _send(self, method, path, body=None, raw=None, content_type=None):
        headers = {'Authorization': f'Bearer {self.token}', 'Accept': 'application/json'}
        data = None
        if raw is not None:
            data, headers['Content-Type'] = raw, content_type
        elif body is not None:
            data, headers['Content-Type'] = json.dumps(body).encode(), 'application/json'
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                text = r.read().decode('utf-8') or 'null'
                return json.loads(text) if 'json' in (r.headers.get('Content-Type') or '') else text
        except urllib.error.HTTPError as e:
            try:
                message = json.loads(e.read().decode('utf-8')).get('message')
            except Exception:
                message = e.reason
            raise PlatformError(e.code, message) from None

    def get(self, path):
        return self._send('GET', path)

    def post(self, path, body=None):
        return self._send('POST', path, body if body is not None else {})

    def patch(self, path, body):
        return self._send('PATCH', path, body)

    def upload(self, path, field, data, filename='banner.jpg', mime='image/jpeg'):
        boundary = uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                f'Content-Type: {mime}\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
        return self._send('POST', path, raw=body, content_type=f'multipart/form-data; boundary={boundary}')
