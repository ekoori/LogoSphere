# Pytest bootstrap. Apply the gevent monkeypatch before anything imports
# cassandra.cluster: on Python 3.12+ the driver's default reactor relies on
# asyncore (removed), so importing the models would otherwise raise
# DependencyException during test collection.
from gevent import monkey
monkey.patch_all()

import os
import sys
import pytest


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """The models open a live Cassandra cluster connection at import time, whose
    background threads (under the gevent reactor) keep the interpreter from
    exiting cleanly. Force exit after the run, preserving pytest's status code."""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exitstatus)
