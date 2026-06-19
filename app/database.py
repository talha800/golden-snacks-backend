from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Enforce secure connection parameters for cloud architectures
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,           # Maintains up to 10 persistent connections ready to go
    max_overflow=20,        # Dynamically opens up to 20 extra slots under traffic spikes
    pool_timeout=30,        # Waits up to 30 seconds before throwing a timeout error
    pool_pre_ping=True,     # Safeguards against broken pipe dropouts
    connect_args={
        "sslmode": "require",         # Explicitly forces SSL encryption
        "options": "-c prepare_threshold=0" # Safely injects the Supabase pooler threshold parameter
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()