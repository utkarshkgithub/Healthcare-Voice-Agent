"""
Database connection pool.

Config is validated before the pool is built, so a missing DATABASE_URL fails
with an actionable message instead of a driver-level traceback at import time.
"""
import logging

from psycopg_pool import ConnectionPool

from config import Config

logger = logging.getLogger(__name__)

Config.validate()

#: Bounded so a traffic spike cannot open unbounded connections against
#: Postgres. Tune against the server's max_connections.
pool = ConnectionPool(
    conninfo=Config.DATABASE_URL,
    min_size=Config.DB_POOL_MIN_SIZE,
    max_size=Config.DB_POOL_MAX_SIZE,
    timeout=Config.DB_POOL_TIMEOUT,
    open=True,
)