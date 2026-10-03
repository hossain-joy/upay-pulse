import sys
import os

# Add root directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from sqlalchemy import inspect
from backend.app.core.database import engine
from backend.app.models import Base

def init_database():
    print(f"Creating all tables for upay Pulse on: {engine.url.render_as_string(hide_password=True)}")
    Base.metadata.create_all(bind=engine)
    
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    print("\nVerified created tables in database:")
    for t in tables:
        columns = [col['name'] for col in inspector.get_columns(t)]
        print(f"  [OK] {t} ({len(columns)} columns)")
    print(f"\nTotal tables created: {len(tables)}")
    return tables

if __name__ == "__main__":
    init_database()
