import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

logger = logging.getLogger("upay_pulse.database")

Base = declarative_base()

def get_engine():
    """Create SQLAlchemy engine with automatic fallback to SQLite if PostgreSQL fails."""
    try:
        db_url = settings.DATABASE_URL
        # Normalize Render/Heroku postgres:// schema to SQLAlchemy postgresql+psycopg2://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected successfully to PostgreSQL: %s", db_url.split('@')[-1])
        return engine
    except Exception as e:
        logger.warning(
            "Failed connecting to PostgreSQL (%s). Falling back to SQLite: %s",
            str(e).strip(),
            settings.SQLITE_FALLBACK_URL
        )
        engine = create_engine(
            settings.SQLITE_FALLBACK_URL,
            connect_args={"check_same_thread": False},
            echo=False
        )
        return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency yield for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_health() -> dict:
    """Verify database responsiveness."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            dialect = engine.dialect.name
            return {
                "status": "healthy" if result == 1 else "unhealthy",
                "dialect": dialect,
                "database": "upay_pulse" if dialect == "postgresql" else "sqlite"
            }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "error": str(exc)
        }
