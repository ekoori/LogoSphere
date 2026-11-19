# Production WSGI entrypoint (gunicorn --worker-class gthread ... wsgi:app).
# reactor picks the Cassandra driver's event loop before the driver loads:
# libev on the host, so the workers run ordinary threads - no monkey-patching.
import reactor  # noqa: F401
from app.main import app  # noqa: E402

application = app
