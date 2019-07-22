import datetime
import webtest.app


# ==============================================================================


class FakeRegistry(object):
    """
    fake object for FakeRequest
    """
    settings = None


class FakeRequest(object):
    """
    fake object, needs FakeAppMeta
    current version
    """
    _method = None
    _post = None
    dbSession = None
    datetime = None
    active_useraccount_id = None

    def __init__(self):
        self.datetime = datetime.datetime.utcnow()
        self.registry = FakeRegistry()
        self.headers = []

    def current_route_url(self, uri=None):
        if uri is not None:
            self._current_route_url = uri
        return self._current_route_url

    @property
    def method(self):
        return self._method or 'GET'

    @property
    def POST(self):
        return self._post or {}


def parse_request_simple(req):
    if '?' in req.url:
        _path, _qs = req.url.split('?')
    else:
        _path = req.url
        _qs = ''
    return (_path, _qs)


class IsolatedTestapp(object):
    """
    This class offers a ContextManger that uses it's own cookiejar

    Requirements:
        import webtest.app

    Attributes:
        ``testapp`` active ``webtest.TestApp`` instance
        ``cookiejar_original`` original cookiejar for testapp. It will be replaced on exit.
        ``cookiejar_local`` local cookiejar to context manager.
    """
    testapp = None
    cookiejar_original = None
    cookiejar_local = None

    def __init__(self, testapp, cookiejar=None):
        """
        args:
            ``testapp`` active ``webtest.TestApp`` instance
        kwargs:
            ``cookiejar`` standard library ``CookieJar`` compatible instance, or ``None`` to create an automated jar
        """
        self.testapp = testapp
        self.cookiejar_original = testapp.cookiejar
        if cookiejar is None:
            cookiejar = webtest.app.http_cookiejar.CookieJar(policy=webtest.app.CookiePolicy())
        self.cookiejar_local = testapp.cookiejar = cookiejar

    def __enter__(self):
        return self.testapp

    def __exit__(self, *args):
        self.testapp.cookiejar = self.cookiejar_original
