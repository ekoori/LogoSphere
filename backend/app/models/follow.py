# Follow model — a directed "follows" edge between users, backed by the
# logosphere.follows table (PK (follower_id, followee_id)). Lets a user follow
# others and drives the "Following" feed on Home.
import uuid
import os
import logging
from datetime import datetime

from app.db import session as cassandra_session


class Follow:
    @classmethod
    def is_following(cls, follower_id, followee_id):
        try:
            row = cassandra_session.execute(
                "SELECT followee_id FROM follows WHERE follower_id = %s AND followee_id = %s",
                [uuid.UUID(str(follower_id)), uuid.UUID(str(followee_id))]
            ).one()
            return row is not None
        except Exception as e:
            logging.error(f"Error checking follow: {e}")
            return False

    @classmethod
    def toggle(cls, follower_id, followee_id):
        """Follow if not already, unfollow if already. Returns the new state."""
        f = uuid.UUID(str(follower_id))
        t = uuid.UUID(str(followee_id))
        if cls.is_following(f, t):
            cassandra_session.execute(
                "DELETE FROM follows WHERE follower_id = %s AND followee_id = %s", [f, t])
            return False
        cassandra_session.execute(
            "INSERT INTO follows (follower_id, followee_id, created_at) VALUES (%s, %s, %s)",
            [f, t, datetime.utcnow()])
        return True

    @classmethod
    def following_ids(cls, follower_id):
        try:
            rows = cassandra_session.execute(
                "SELECT followee_id FROM follows WHERE follower_id = %s",
                [uuid.UUID(str(follower_id))])
            return [r.followee_id for r in rows]
        except Exception as e:
            logging.error(f"Error listing following: {e}")
            return []

    @classmethod
    def following_count(cls, follower_id):
        return len(cls.following_ids(follower_id))
