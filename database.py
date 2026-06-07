from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import threading

from config import Config

Config.ensure_dirs()

engine = create_engine(
    Config.DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
SessionLocal = scoped_session(SessionFactory)

Base = declarative_base()

_thread_local = threading.local()


@contextmanager
def get_db_session():
    if not hasattr(_thread_local, 'session'):
        _thread_local.session = SessionLocal()
    session = _thread_local.session
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        pass


def init_db():
    Base.metadata.create_all(bind=engine)


def close_session():
    if hasattr(_thread_local, 'session'):
        _thread_local.session.close()
        delattr(_thread_local, 'session')
