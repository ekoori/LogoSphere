"""Now, in naive UTC: how Cassandra hands timestamps back, and what the agents
compare them with (datetime.utcnow is deprecated)."""
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
