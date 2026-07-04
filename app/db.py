from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .paths import DATA_DIR

DB_PATH = DATA_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

def ensure_schema_upgraded(engine):
    try:
        with engine.begin() as conn:
            # Check lease_placements columns
            columns_lp = [row[1] for row in conn.execute(text("PRAGMA table_info(lease_placements)")).fetchall()]
            if columns_lp:
                if "rent_tariff" not in columns_lp:
                    conn.execute(text("ALTER TABLE lease_placements ADD COLUMN rent_tariff NUMERIC"))
                if "status" not in columns_lp:
                    conn.execute(text("ALTER TABLE lease_placements ADD COLUMN status VARCHAR DEFAULT 'active'"))
                if "comment" not in columns_lp:
                    conn.execute(text("ALTER TABLE lease_placements ADD COLUMN comment VARCHAR"))

            # Check charge_allocations columns
            columns_ca = [row[1] for row in conn.execute(text("PRAGMA table_info(charge_allocations)")).fetchall()]
            if columns_ca:
                if "placement_id" not in columns_ca:
                    conn.execute(text("ALTER TABLE charge_allocations ADD COLUMN placement_id INTEGER"))

            # Check tenants columns
            columns_t = [row[1] for row in conn.execute(text("PRAGMA table_info(tenants)")).fetchall()]
            if columns_t:
                if "initial_balance" not in columns_t:
                    conn.execute(text("ALTER TABLE tenants ADD COLUMN initial_balance NUMERIC DEFAULT 0"))
    except Exception as e:
        print(f"Schema upgrade check failed: {e}")

ensure_schema_upgraded(engine)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
