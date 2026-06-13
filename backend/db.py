# db.py
from psycopg_pool import ConnectionPool
from config import Config

pool = ConnectionPool(conninfo=Config.DATABASE_URL)