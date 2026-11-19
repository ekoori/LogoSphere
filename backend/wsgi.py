# Production WSGI entrypoint. gevent must monkey-patch before the cassandra
# driver is imported (Python 3.12 removed asyncore; the driver auto-selects its
# gevent reactor once patching is detected).
from gevent import monkey
monkey.patch_all()
from app.main import app  # noqa: E402

application = app
