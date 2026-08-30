"""Kết nối cơ sở dữ liệu (SQLAlchemy 2.0)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_session():
    """Cấp một phiên làm việc DB (dùng cho FastAPI Depends hoặc thủ công)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Tạo bảng dựa trên các model đã khai báo. Gọi một lần khi khởi tạo."""
    import storage.models  # noqa: F401  đảm bảo model được import trước create_all
    Base.metadata.create_all(bind=engine)
