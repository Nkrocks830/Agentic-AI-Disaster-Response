import sys
sys.path.insert(0, '.')
from database.db_manager import initialize_database, execute_write
from database.seed_data import seed_all

print("Cleaning tables and re-seeding database...")
initialize_database()

# List of all tables to clear in reverse dependency order
tables = [
    "notifications",
    "agent_logs",
    "patient_allocations",
    "emergency_requests",
    "ambulances",
    "resources",
    "roads",
    "shelters",
    "disasters",
    "hospitals",
    "users"
]

# Delete all rows from each table
for table in tables:
    try:
        execute_write(f"DELETE FROM {table}")
        execute_write(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
    except Exception as e:
        print(f"Warning clearing {table}: {e}")

# Run seed
seed_all()
print("Clean reset and re-seed completed successfully!")
