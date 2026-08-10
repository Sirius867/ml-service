import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    if database_url := os.getenv("DATABASE_URL"):
        return database_url

    host = os.getenv("DATABASE_HOST")
    port = os.getenv("DATABASE_PORT")
    name = os.getenv("DATABASE_NAME")
    user = os.getenv("DATABASE_USER")
    password = os.getenv("DATABASE_PASSWORD")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


engine: Engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
