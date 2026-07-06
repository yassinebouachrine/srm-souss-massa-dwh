"""
============================================================
SRM Souss-Massa - Connexion PostgreSQL
============================================================
"""

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from contextlib import contextmanager
from streamlit_app.config.settings import settings


@st.cache_resource
def get_engine():
    """Créer l'engine SQLAlchemy (cache)"""
    return create_engine(
        settings.db_connection_string,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )


@contextmanager
def get_db_connection():
    """Context manager pour psycopg2"""
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        cursor_factory=RealDictCursor
    )
    try:
        yield conn
    finally:
        conn.close()


def test_connection():
    """Tester la connexion"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT version()")
            return True, cur.fetchone()['version']
    except Exception as e:
        return False, str(e)