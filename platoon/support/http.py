import socket
from httplib import HTTPConnection, HTTPSConnection
from urlparse import urlparse

from scheme import formats
from mesh.exceptions import *

class Response(object):
    def __init__(self, status, reason, mimetype, content, headers):
        self.content = content
        self.headers = headers
        self.mimetype = mimetype
        self.reason = reason
        self.status = status

    @property
    def exception(self):
        return RequestError.construct(self.status, self.dump())

    @property
    def ok(self):
        return (200 <= self.status <= 299)

    def dump(self):
        lines = ['%s %s' % (self.status, self.reason)]
        for header, value in sorted(self.headers.iteritems()):
            lines.append('%s: %s' % (header, value))

        if self.content:
            lines.extend(['', self.content])
        return '\n'.join(lines)

    def unserialize(self):
        if self.content:
            return formats.unserialize(self.mimetype, self.content)

def http_request(method, url, body=None, mimetype=None, headers=None,
        timeout=None, serialize=False):

    scheme, host, path = urlparse(url)[:3]
    if scheme == 'https':
        connection = HTTPSConnection(host=host, timeout=timeout)
    else:
        connection = HTTPConnection(host=host, timeout=timeout)

    if body:
        if method == 'GET':
            path = '%s?%s' % (path, body)
            body = None
        elif serialize:
            if mimetype:
                body = formats.serialize(mimetype, body)
            else:
                raise ValueError(mimetype)

    headers = headers or {}
    if 'Content-Type' not in headers and mimetype:
        headers['Content-Type'] = mimetype

    connection.request(method, path, body, headers)
    response = connection.getresponse()

    headers = dict((key.title(), value) for key, value in response.getheaders())
    content = response.read() or None

    mimetype = response.getheader('Content-Type', None)
    return Response(response.status, response.reason, mimetype, content, headers)
