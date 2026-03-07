from __future__ import annotations

import os
from sqlmodel import SQLModel, create_engine


def get_db_url() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(data_dir, 'app.db')}"


engine = create_engine(get_db_url(), echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
