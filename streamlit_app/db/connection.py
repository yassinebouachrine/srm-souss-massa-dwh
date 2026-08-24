# db/connection.py
import psycopg2
from psycopg2 import pool, extras
from contextlib import contextmanager
import streamlit as st
from config.settings import DB_CONFIG
import logging

logger = logging.getLogger(__name__)


def init_connection_pool():
    """Initialize the database connection pool."""
    try:
        return psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
        )
    except Exception as e:
        logger.error(f"Erreur connexion DB: {e}")
        st.error(f"❌ Impossible de se connecter à la base de données: {e}")
        return None


@st.cache_resource
def get_pool():
    """Get or create cached connection pool."""
    return init_connection_pool()


@contextmanager
def get_connection():
    """Context manager for database connections."""
    _pool = get_pool()
    if _pool is None:
        raise Exception("Pool de connexion non disponible")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur DB: {e}")
        raise
    finally:
        _pool.putconn(conn)


def execute_query(query: str, params: tuple = None, fetch: str = "all"):
    """Execute a query and return results."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch == "all":
                return cur.fetchall()
            elif fetch == "one":
                return cur.fetchone()
            elif fetch == "none":
                return None


def execute_insert(query: str, params: tuple = None):
    """Execute an insert/update query."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            try:
                return cur.fetchone()
            except:
                return None


def execute_many(query: str, params_list: list):
    """Execute multiple insert/update queries."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            extras.execute_batch(cur, query, params_list)