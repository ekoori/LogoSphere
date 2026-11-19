"""Choose the Cassandra driver's event loop. Import this before anything that
imports the driver.

Python 3.12 removed asyncore, the driver's old default. Where the driver's
libev extension is built (the Linux production host) the driver picks it up by
itself, and gunicorn runs plain threads. Elsewhere (e.g. a Windows dev machine)
fall back to gevent, which has to monkey-patch the standard library before the
driver loads. The gevent reactor is deprecated in the driver, and reading large
blobs through it stalled connections in production - so it is only a fallback.
"""
import importlib.util

try:
    HAVE_LIBEV = importlib.util.find_spec('cassandra.io.libevwrapper') is not None
except ImportError:
    HAVE_LIBEV = False

if HAVE_LIBEV:
    REACTOR = 'libev'
else:
    from gevent import monkey

    monkey.patch_all()
    REACTOR = 'gevent'
