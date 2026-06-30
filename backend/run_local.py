# Local dev runner — applies gevent monkeypatch before importing the cassandra driver.
# Python 3.13 removed asyncore, so the driver cannot start its default reactor without
# either gevent or a libev C extension. Run from the backend/ directory:
#   PYTHONPATH=backend python run_local.py

from gevent import monkey
monkey.patch_all()

import os
os.environ.setdefault('CASSANDRA_HOST', '127.0.0.1')

from gevent.pywsgi import WSGIServer
from app.main import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'Starting LogoSphere backend on http://0.0.0.0:{port}')
    server = WSGIServer(('0.0.0.0', port), app)
    server.serve_forever()
