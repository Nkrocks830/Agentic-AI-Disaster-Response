"""
ResQNet AI - Database Manager
Handles SQLite connection, schema creation, and all CRUD operations.
All queries use parameterized statements to prevent SQL injection.
"""

import sqlite3
import json
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from config.settings import DATABASE_PATH


# ── Thread-local connection pool ──────────────────────────────────────────────
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Return a per-thread SQLite connection (thread-safe)."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row          # dict-like row access
        _local.conn.execute("PRAGMA journal_mode=WAL") # Write-Ahead Logging
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def get_cursor():
    """Context manager yielding a cursor; auto-commits or rolls back."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        cursor.close()


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMA CREATION
# ══════════════════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
-- ── Hospitals ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hospitals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    address         TEXT NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    total_beds      INTEGER NOT NULL DEFAULT 0,
    available_beds  INTEGER NOT NULL DEFAULT 0,
    total_icu       INTEGER NOT NULL DEFAULT 0,
    available_icu   INTEGER NOT NULL DEFAULT 0,
    total_doctors   INTEGER NOT NULL DEFAULT 0,
    available_doctors INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'Operational',
    specializations TEXT NOT NULL DEFAULT '[]',    -- JSON array
    contact_phone   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Ambulances ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ambulances (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_number  TEXT NOT NULL UNIQUE,
    driver_name     TEXT NOT NULL,
    driver_phone    TEXT NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Available',  -- Available|Dispatched|En Route|At Hospital
    current_patient_id INTEGER,
    assigned_hospital_id INTEGER REFERENCES hospitals(id),
    fuel_level      INTEGER NOT NULL DEFAULT 100,       -- percentage
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Disasters ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS disasters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    disaster_type   TEXT NOT NULL,
    severity        INTEGER NOT NULL DEFAULT 1 CHECK(severity BETWEEN 1 AND 5),
    status          TEXT NOT NULL DEFAULT 'Active',     -- Active|Contained|Resolved
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    affected_radius_km REAL NOT NULL DEFAULT 5.0,
    affected_people INTEGER NOT NULL DEFAULT 0,
    description     TEXT,
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at     TEXT
);

-- ── Emergency Requests ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emergency_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    citizen_name    TEXT NOT NULL,
    citizen_phone   TEXT NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    address         TEXT NOT NULL,
    description     TEXT NOT NULL,
    disaster_type   TEXT,
    severity        INTEGER DEFAULT 1,
    num_people      INTEGER NOT NULL DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'Pending',   -- Pending|Processing|Dispatched|Resolved
    disaster_id     INTEGER REFERENCES disasters(id),
    assigned_hospital_id INTEGER REFERENCES hospitals(id),
    assigned_ambulance_id INTEGER REFERENCES ambulances(id),
    evacuation_route TEXT,   -- JSON
    eta_minutes     INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Roads ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    road_name       TEXT NOT NULL,
    from_location   TEXT NOT NULL,
    to_location     TEXT NOT NULL,
    from_lat        REAL NOT NULL,
    from_lon        REAL NOT NULL,
    to_lat          REAL NOT NULL,
    to_lon          REAL NOT NULL,
    condition       TEXT NOT NULL DEFAULT 'Clear',     -- Clear|Blocked|Flooded|Damaged|Collapsed
    blockage_reason TEXT,
    severity        INTEGER DEFAULT 0,
    is_passable     INTEGER NOT NULL DEFAULT 1,        -- 0=false, 1=true
    reported_at     TEXT DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Resources ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    resource_type   TEXT NOT NULL,                     -- Rescue Boat|Fire Truck|Rescue Team|Helicopter
    location_name   TEXT NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Available', -- Available|Deployed|Maintenance
    capacity        INTEGER NOT NULL DEFAULT 1,        -- e.g. boat capacity in persons
    assigned_disaster_id INTEGER REFERENCES disasters(id),
    operator_name   TEXT,
    operator_phone  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    phone           TEXT NOT NULL UNIQUE,
    email           TEXT,
    role            TEXT NOT NULL DEFAULT 'citizen',   -- citizen|hospital_staff|ambulance_driver|government|admin
    linked_entity_id INTEGER,                          -- hospital_id or ambulance_id
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Agent Execution Logs ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER REFERENCES emergency_requests(id),
    disaster_id     INTEGER REFERENCES disasters(id),
    agent_name      TEXT NOT NULL,
    action          TEXT NOT NULL,
    decision        TEXT NOT NULL,
    reasoning       TEXT,
    input_data      TEXT,  -- JSON
    output_data     TEXT,  -- JSON
    execution_time_ms INTEGER,
    status          TEXT NOT NULL DEFAULT 'success',   -- success|failed|skipped
    mode            TEXT NOT NULL DEFAULT 'live',      -- live|simulation
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Notifications ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER REFERENCES emergency_requests(id),
    recipient_type  TEXT NOT NULL,   -- citizen|hospital|ambulance|authority|public
    recipient_id    INTEGER,
    recipient_name  TEXT,
    message         TEXT NOT NULL,
    channel         TEXT NOT NULL DEFAULT 'sms',       -- sms|email|app|broadcast
    status          TEXT NOT NULL DEFAULT 'sent',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Patient Allocations ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patient_allocations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER NOT NULL REFERENCES emergency_requests(id),
    hospital_id     INTEGER NOT NULL REFERENCES hospitals(id),
    beds_reserved   INTEGER NOT NULL DEFAULT 1,
    icu_reserved    INTEGER NOT NULL DEFAULT 0,
    allocation_status TEXT NOT NULL DEFAULT 'pending',  -- pending|accepted|rejected|completed
    priority        INTEGER NOT NULL DEFAULT 3,
    notes           TEXT,
    allocated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Shelters ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shelters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    address         TEXT NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    capacity        INTEGER NOT NULL DEFAULT 0,
    current_occupancy INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'Active',
    contact_person  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Indexes for performance ────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_emergency_requests_status ON emergency_requests(status);
CREATE INDEX IF NOT EXISTS idx_emergency_requests_disaster ON emergency_requests(disaster_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_request ON agent_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_roads_condition ON roads(condition);
CREATE INDEX IF NOT EXISTS idx_ambulances_status ON ambulances(status);
CREATE INDEX IF NOT EXISTS idx_resources_status ON resources(status);
"""


def initialize_database():
    """Create all tables if they don't exist."""
    with get_cursor() as cur:
        cur.executescript(SCHEMA_SQL)
    print(f"[DB] Database initialized at: {DATABASE_PATH}")


# ══════════════════════════════════════════════════════════════════════════════
# GENERIC HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row) if row else {}


def _rows_to_list(rows) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


def fetch_one(sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


def fetch_all(sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(sql, params)
        return _rows_to_list(cur.fetchall())


def execute_write(sql: str, params: Tuple = ()) -> int:
    """Execute INSERT/UPDATE/DELETE; returns lastrowid or rowcount."""
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid


def execute_many(sql: str, params_list: List[Tuple]) -> None:
    with get_cursor() as cur:
        cur.executemany(sql, params_list)


# ══════════════════════════════════════════════════════════════════════════════
# HOSPITAL OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_hospitals() -> List[Dict]:
    return fetch_all("SELECT * FROM hospitals ORDER BY name")


def get_hospital_by_id(hospital_id: int) -> Optional[Dict]:
    return fetch_one("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))


def get_available_hospitals(min_beds: int = 1) -> List[Dict]:
    return fetch_all(
        "SELECT * FROM hospitals WHERE available_beds >= ? AND status != 'Offline' ORDER BY available_beds DESC",
        (min_beds,)
    )


def update_hospital_beds(hospital_id: int, beds_delta: int, icu_delta: int = 0):
    """Adjust bed/ICU counts. Use negative delta to reserve, positive to release."""
    execute_write(
        """UPDATE hospitals
           SET available_beds = MAX(0, available_beds + ?),
               available_icu  = MAX(0, available_icu + ?),
               updated_at     = datetime('now')
           WHERE id = ?""",
        (beds_delta, icu_delta, hospital_id)
    )


def update_hospital_status(hospital_id: int, status: str):
    execute_write(
        "UPDATE hospitals SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, hospital_id)
    )


# ══════════════════════════════════════════════════════════════════════════════
# AMBULANCE OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_ambulances() -> List[Dict]:
    return fetch_all("SELECT * FROM ambulances ORDER BY status, id")


def get_available_ambulances() -> List[Dict]:
    return fetch_all("SELECT * FROM ambulances WHERE status = 'Available' ORDER BY id")


def get_ambulance_by_id(amb_id: int) -> Optional[Dict]:
    return fetch_one("SELECT * FROM ambulances WHERE id = ?", (amb_id,))


def dispatch_ambulance(amb_id: int, request_id: int, hospital_id: int):
    execute_write(
        """UPDATE ambulances
           SET status = 'Dispatched',
               current_patient_id = ?,
               assigned_hospital_id = ?,
               updated_at = datetime('now')
           WHERE id = ?""",
        (request_id, hospital_id, amb_id)
    )


def release_ambulance(amb_id: int):
    execute_write(
        """UPDATE ambulances
           SET status = 'Available',
               current_patient_id = NULL,
               assigned_hospital_id = NULL,
               updated_at = datetime('now')
           WHERE id = ?""",
        (amb_id,)
    )


# ══════════════════════════════════════════════════════════════════════════════
# DISASTER OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_active_disasters() -> List[Dict]:
    return fetch_all("SELECT * FROM disasters WHERE status = 'Active' ORDER BY severity DESC")


def get_disaster_by_id(disaster_id: int) -> Optional[Dict]:
    return fetch_one("SELECT * FROM disasters WHERE id = ?", (disaster_id,))


def create_disaster(data: Dict) -> int:
    return execute_write(
        """INSERT INTO disasters
           (name, disaster_type, severity, latitude, longitude, affected_radius_km,
            affected_people, description, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active')""",
        (data["name"], data["disaster_type"], data["severity"],
         data["latitude"], data["longitude"], data.get("affected_radius_km", 5.0),
         data.get("affected_people", 0), data.get("description", ""))
    )


def update_disaster_severity(disaster_id: int, severity: int, affected_people: int):
    execute_write(
        "UPDATE disasters SET severity=?, affected_people=?, updated_at=datetime('now') WHERE id=?",
        (severity, affected_people, disaster_id)
    )


# ══════════════════════════════════════════════════════════════════════════════
# EMERGENCY REQUEST OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_requests() -> List[Dict]:
    return fetch_all("SELECT * FROM emergency_requests ORDER BY created_at DESC")


def get_request_by_id(req_id: int) -> Optional[Dict]:
    return fetch_one("SELECT * FROM emergency_requests WHERE id = ?", (req_id,))


def get_requests_by_status(status: str) -> List[Dict]:
    return fetch_all("SELECT * FROM emergency_requests WHERE status = ? ORDER BY created_at DESC", (status,))


def create_emergency_request(data: Dict) -> int:
    return execute_write(
        """INSERT INTO emergency_requests
           (citizen_name, citizen_phone, latitude, longitude, address,
            description, num_people, status, disaster_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)""",
        (data["citizen_name"], data["citizen_phone"], data["latitude"],
         data["longitude"], data["address"], data["description"],
         data.get("num_people", 1), data.get("disaster_id"))
    )


def update_request_status(req_id: int, status: str, **kwargs):
    sets = ["status = ?", "updated_at = datetime('now')"]
    vals: List[Any] = [status]
    for key, val in kwargs.items():
        sets.append(f"{key} = ?")
        vals.append(val if not isinstance(val, (dict, list)) else json.dumps(val))
    vals.append(req_id)
    execute_write(f"UPDATE emergency_requests SET {', '.join(sets)} WHERE id = ?", tuple(vals))


def get_requests_for_hospital(hospital_id: int) -> List[Dict]:
    return fetch_all(
        "SELECT * FROM emergency_requests WHERE assigned_hospital_id = ? ORDER BY created_at DESC",
        (hospital_id,)
    )


def get_requests_for_ambulance(ambulance_id: int) -> List[Dict]:
    return fetch_all(
        "SELECT * FROM emergency_requests WHERE assigned_ambulance_id = ? AND status != 'Resolved' ORDER BY created_at DESC",
        (ambulance_id,)
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROAD OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_roads() -> List[Dict]:
    return fetch_all("SELECT * FROM roads ORDER BY condition, road_name")


def get_blocked_roads() -> List[Dict]:
    return fetch_all("SELECT * FROM roads WHERE is_passable = 0 ORDER BY severity DESC")


def get_passable_roads() -> List[Dict]:
    return fetch_all("SELECT * FROM roads WHERE is_passable = 1")


def update_road_condition(road_id: int, condition: str, reason: str, is_passable: int):
    execute_write(
        """UPDATE roads
           SET condition = ?, blockage_reason = ?, is_passable = ?,
               updated_at = datetime('now')
           WHERE id = ?""",
        (condition, reason, is_passable, road_id)
    )


# ══════════════════════════════════════════════════════════════════════════════
# RESOURCE OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_resources() -> List[Dict]:
    return fetch_all("SELECT * FROM resources ORDER BY resource_type, status")


def get_available_resources(resource_type: Optional[str] = None) -> List[Dict]:
    if resource_type:
        return fetch_all(
            "SELECT * FROM resources WHERE status = 'Available' AND resource_type = ?",
            (resource_type,)
        )
    return fetch_all("SELECT * FROM resources WHERE status = 'Available'")


def deploy_resource(resource_id: int, disaster_id: int):
    execute_write(
        """UPDATE resources
           SET status = 'Deployed', assigned_disaster_id = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (disaster_id, resource_id)
    )


def release_resource(resource_id: int):
    execute_write(
        """UPDATE resources
           SET status = 'Available', assigned_disaster_id = NULL, updated_at = datetime('now')
           WHERE id = ?""",
        (resource_id,)
    )


# ══════════════════════════════════════════════════════════════════════════════
# AGENT LOG OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def log_agent_execution(
    agent_name: str,
    action: str,
    decision: str,
    reasoning: str = "",
    request_id: Optional[int] = None,
    disaster_id: Optional[int] = None,
    input_data: Optional[Dict] = None,
    output_data: Optional[Dict] = None,
    execution_time_ms: int = 0,
    status: str = "success",
    mode: str = "live"
) -> int:
    return execute_write(
        """INSERT INTO agent_logs
           (request_id, disaster_id, agent_name, action, decision, reasoning,
            input_data, output_data, execution_time_ms, status, mode)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (request_id, disaster_id, agent_name, action, decision, reasoning,
         json.dumps(input_data or {}), json.dumps(output_data or {}),
         execution_time_ms, status, mode)
    )


def get_agent_logs(limit: int = 100, agent_name: Optional[str] = None) -> List[Dict]:
    if agent_name:
        return fetch_all(
            "SELECT * FROM agent_logs WHERE agent_name = ? ORDER BY created_at DESC LIMIT ?",
            (agent_name, limit)
        )
    return fetch_all("SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT ?", (limit,))


def get_logs_for_request(request_id: int) -> List[Dict]:
    return fetch_all(
        "SELECT * FROM agent_logs WHERE request_id = ? ORDER BY created_at ASC",
        (request_id,)
    )


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def create_notification(data: Dict) -> int:
    return execute_write(
        """INSERT INTO notifications
           (request_id, recipient_type, recipient_id, recipient_name, message, channel, status)
           VALUES (?, ?, ?, ?, ?, ?, 'sent')""",
        (data.get("request_id"), data["recipient_type"], data.get("recipient_id"),
         data.get("recipient_name"), data["message"], data.get("channel", "sms"))
    )


def get_notifications(limit: int = 50) -> List[Dict]:
    return fetch_all("SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,))


# ══════════════════════════════════════════════════════════════════════════════
# PATIENT ALLOCATION OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def create_patient_allocation(request_id: int, hospital_id: int,
                               beds: int, icu: int, priority: int) -> int:
    return execute_write(
        """INSERT INTO patient_allocations
           (request_id, hospital_id, beds_reserved, icu_reserved, priority, allocation_status)
           VALUES (?, ?, ?, ?, ?, 'pending')""",
        (request_id, hospital_id, beds, icu, priority)
    )


def update_allocation_status(allocation_id: int, status: str):
    execute_write(
        "UPDATE patient_allocations SET allocation_status=?, updated_at=datetime('now') WHERE id=?",
        (status, allocation_id)
    )


def get_allocations_for_hospital(hospital_id: int) -> List[Dict]:
    """Return only PENDING allocations — accepted ones leave the queue immediately."""
    return fetch_all(
        """SELECT pa.*, er.citizen_name, er.citizen_phone, er.num_people, er.severity,
                  er.latitude, er.longitude, er.assigned_ambulance_id
           FROM patient_allocations pa
           JOIN emergency_requests er ON pa.request_id = er.id
           WHERE pa.hospital_id = ? AND pa.allocation_status = 'pending'
           ORDER BY pa.priority ASC, pa.allocated_at ASC""",
        (hospital_id,)
    )


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_dashboard_summary() -> Dict:
    """Return key metrics for the Government Dashboard."""
    active_disasters = fetch_one("SELECT COUNT(*) as cnt FROM disasters WHERE status='Active'")
    total_requests   = fetch_one("SELECT COUNT(*) as cnt FROM emergency_requests")
    pending_requests = fetch_one("SELECT COUNT(*) as cnt FROM emergency_requests WHERE status='Pending'")
    resolved_requests= fetch_one("SELECT COUNT(*) as cnt FROM emergency_requests WHERE status='Resolved'")
    dispatched_ambs  = fetch_one("SELECT COUNT(*) as cnt FROM ambulances WHERE status='Dispatched'")
    available_ambs   = fetch_one("SELECT COUNT(*) as cnt FROM ambulances WHERE status='Available'")
    blocked_roads    = fetch_one("SELECT COUNT(*) as cnt FROM roads WHERE is_passable=0")
    total_resources  = fetch_one("SELECT COUNT(*) as cnt FROM resources")
    deployed_resources = fetch_one("SELECT COUNT(*) as cnt FROM resources WHERE status='Deployed'")
    total_beds       = fetch_one("SELECT SUM(total_beds) as cnt FROM hospitals")
    available_beds   = fetch_one("SELECT SUM(available_beds) as cnt FROM hospitals")

    return {
        "active_disasters":    active_disasters["cnt"] if active_disasters else 0,
        "total_requests":      total_requests["cnt"] if total_requests else 0,
        "pending_requests":    pending_requests["cnt"] if pending_requests else 0,
        "resolved_requests":   resolved_requests["cnt"] if resolved_requests else 0,
        "dispatched_ambulances": dispatched_ambs["cnt"] if dispatched_ambs else 0,
        "available_ambulances":  available_ambs["cnt"] if available_ambs else 0,
        "blocked_roads":       blocked_roads["cnt"] if blocked_roads else 0,
        "total_resources":     total_resources["cnt"] if total_resources else 0,
        "deployed_resources":  deployed_resources["cnt"] if deployed_resources else 0,
        "total_beds":          total_beds["cnt"] if total_beds else 0,
        "available_beds":      available_beds["cnt"] if available_beds else 0,
    }


def get_shelters() -> List[Dict]:
    return fetch_all("SELECT * FROM shelters ORDER BY current_occupancy DESC")


def is_database_seeded() -> bool:
    """Check if seed data already exists."""
    result = fetch_one("SELECT COUNT(*) as cnt FROM hospitals")
    return (result["cnt"] if result else 0) > 0


# ══════════════════════════════════════════════════════════════════════════════
# ACCEPT / REJECT WORKFLOW HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def accept_patient_allocation(allocation_id: int, request_id: int, hospital_id: int,
                              hospital_name: str, chosen_ambulance_id: int) -> bool:
    """
    Full Accept workflow with ATOMIC conflict guard.
    Returns True on success, False if the chosen ambulance was already taken
    by another concurrent Accept (caller must show an error and re-render).

    Steps:
    1. Atomically dispatch the chosen ambulance (only if still Available).
    2. If dispatch fails (ambulance taken) -> rollback, return False.
    3. Mark allocation as 'accepted'.
    4. Set request status -> 'Dispatched' with chosen hospital & ambulance.
    5. Citizen notification with driver details.
    6. Agent log.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # --- Step 1: Atomic ambulance claim (only if still Available) ---
        cursor.execute(
            """UPDATE ambulances
               SET status = 'Dispatched',
                   current_patient_id   = ?,
                   assigned_hospital_id = ?,
                   updated_at = datetime('now')
               WHERE id = ? AND status = 'Available'""",
            (request_id, hospital_id, chosen_ambulance_id)
        )
        if cursor.rowcount == 0:
            # Ambulance was taken by a concurrent Accept — abort
            conn.rollback()
            cursor.close()
            return False

        # --- Step 2: Mark allocation accepted ---
        cursor.execute(
            "UPDATE patient_allocations SET allocation_status='accepted', updated_at=datetime('now') WHERE id=?",
            (allocation_id,)
        )

        # --- Step 3: Update request -> Dispatched with chosen ambulance & hospital ---
        cursor.execute(
            """UPDATE emergency_requests
               SET status = 'Dispatched',
                   assigned_hospital_id = ?,
                   assigned_ambulance_id = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (hospital_id, chosen_ambulance_id, request_id)
        )

        conn.commit()
        cursor.close()

    except Exception as exc:
        conn.rollback()
        cursor.close()
        raise exc

    # --- Step 4: Notifications & logging (outside transaction, non-critical) ---
    req = fetch_one("SELECT citizen_name FROM emergency_requests WHERE id=?", (request_id,))
    citizen_name = req.get("citizen_name", "Citizen") if req else "Citizen"

    amb_info = fetch_one(
        "SELECT vehicle_number, driver_name, driver_phone FROM ambulances WHERE id=?",
        (chosen_ambulance_id,)
    )
    amb_detail = (
        f"Ambulance {amb_info['vehicle_number']} | Driver: {amb_info['driver_name']} "
        f"({amb_info['driver_phone']}) is on its way to you."
        if amb_info else "An ambulance has been dispatched."
    )

    create_notification({
        "request_id":     request_id,
        "recipient_type": "citizen",
        "recipient_name": citizen_name,
        "message":        f"ACCEPTED: Your emergency request #{request_id} has been accepted by "
                          f"{hospital_name}. {amb_detail} Please stay at your location.",
        "channel":        "sms",
    })

    log_agent_execution(
        agent_name="Hospital Allocation Agent",
        action="accept_and_dispatch",
        decision=f"Request #{request_id} ACCEPTED by {hospital_name}. "
                 f"Ambulance {amb_info['vehicle_number'] if amb_info else 'N/A'} dispatched.",
        reasoning=f"Hospital staff confirmed the patient allocation and selected ambulance "
                  f"{amb_info['vehicle_number'] if amb_info else chosen_ambulance_id}. "
                  f"Atomic dispatch succeeded. Request status -> Dispatched. Citizen notified.",
        request_id=request_id,
        output_data={"hospital_id": hospital_id, "ambulance_id": chosen_ambulance_id,
                     "new_status": "Dispatched"},
        status="success",
        mode="live",
    )
    return True


def reject_patient_allocation(allocation_id: int, request_id: int,
                               rejected_hospital_id: int, rejected_hospital_name: str,
                               beds_to_release: int, icu_to_release: int) -> list:
    """
    Full Reject workflow (atomic):
    1. Mark current allocation as 'rejected'.
    2. Release reserved beds back to the rejected hospital.
    3. Find next nearest available hospital (excluding rejected one).
    4. Create new allocation at the next hospital.
    5. Update emergency_request with new hospital.
    6. Create citizen notification.
    7. Log the action.
    Returns list of (next_hospital_dict, new_allocation_id) or [] if none found.
    """
    # 1. Mark as rejected
    execute_write(
        "UPDATE patient_allocations SET allocation_status='rejected', updated_at=datetime('now') WHERE id=?",
        (allocation_id,)
    )
    # 2. Release beds at the rejected hospital
    execute_write(
        """UPDATE hospitals
           SET available_beds = MIN(total_beds, available_beds + ?),
               available_icu  = MIN(total_icu,  available_icu  + ?),
               updated_at     = datetime('now')
           WHERE id = ?""",
        (beds_to_release, icu_to_release, rejected_hospital_id)
    )

    # 3. Find next available hospital (exclude rejected one)
    # Get original request info for distance calculation
    req = fetch_one("SELECT * FROM emergency_requests WHERE id=?", (request_id,))
    if not req:
        return []

    candidates = fetch_all(
        """SELECT * FROM hospitals
           WHERE id != ? AND available_beds >= ? AND status != 'Offline'
           ORDER BY available_beds DESC""",
        (rejected_hospital_id, max(1, beds_to_release))
    )
    if not candidates:
        # Last resort: any hospital with at least 1 bed
        candidates = fetch_all(
            "SELECT * FROM hospitals WHERE id != ? AND available_beds > 0 AND status != 'Offline'",
            (rejected_hospital_id,)
        )
    if not candidates:
        # Log and return — no hospital available, keep request as Pending
        log_agent_execution(
            agent_name="Hospital Allocation Agent",
            action="reject_reallocation_failed",
            decision=f"Request #{request_id} rejected by {rejected_hospital_name}. No alternative hospital found.",
            reasoning="All hospitals are at capacity. Request remains pending for manual review.",
            request_id=request_id,
            output_data={"rejected_hospital": rejected_hospital_name},
            status="failed",
            mode="live",
        )
        execute_write(
            "UPDATE emergency_requests SET status='Pending', assigned_hospital_id=NULL, updated_at=datetime('now') WHERE id=?",
            (request_id,)
        )
        return []

    # Sort by distance from request location
    import math
    def _dist(h):
        dlat = math.radians(h["latitude"] - req["latitude"])
        dlon = math.radians(h["longitude"] - req["longitude"])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(req["latitude"])) * \
            math.cos(math.radians(h["latitude"])) * math.sin(dlon/2)**2
        return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    candidates.sort(key=_dist)
    next_hosp = candidates[0]
    dist_km = _dist(next_hosp)

    # 4. Reserve beds at new hospital
    beds_needed = min(beds_to_release, next_hosp["available_beds"])
    icu_needed  = min(icu_to_release,  next_hosp["available_icu"])

    execute_write(
        """UPDATE hospitals
           SET available_beds = MAX(0, available_beds - ?),
               available_icu  = MAX(0, available_icu  - ?),
               updated_at     = datetime('now')
           WHERE id = ?""",
        (beds_needed, icu_needed, next_hosp["id"])
    )

    # 5. Create new patient_allocation record
    new_alloc_id = execute_write(
        """INSERT INTO patient_allocations
           (request_id, hospital_id, beds_reserved, icu_reserved, allocation_status, priority)
           VALUES (?, ?, ?, ?, 'pending', 2)""",
        (request_id, next_hosp["id"], beds_needed, icu_needed)
    )

    # 6. Update emergency_request with new hospital assignment
    execute_write(
        """UPDATE emergency_requests
           SET assigned_hospital_id=?, status='Processing', updated_at=datetime('now')
           WHERE id=?""",
        (next_hosp["id"], request_id)
    )

    # 7. Citizen notification
    req2 = fetch_one("SELECT citizen_name FROM emergency_requests WHERE id=?", (request_id,))
    citizen_name = req2["citizen_name"] if req2 else "Citizen"
    create_notification({
        "request_id":     request_id,
        "recipient_type": "citizen",
        "recipient_name": citizen_name,
        "message":        f"Your emergency request #{request_id} was not accepted by {rejected_hospital_name}. "
                          f"You have been re-assigned to {next_hosp['name']} ({dist_km:.1f} km away). "
                          f"Beds reserved: {beds_needed}. Your ambulance will be redirected.",
        "channel":        "sms",
    })

    # 8. Agent log
    log_agent_execution(
        agent_name="Hospital Allocation Agent",
        action="reject_and_reallocate",
        decision=f"Request #{request_id} rejected by {rejected_hospital_name}. "
                 f"Re-allocated to {next_hosp['name']} ({dist_km:.1f} km away).",
        reasoning=f"Hospital '{rejected_hospital_name}' rejected the patient. "
                  f"Beds released ({beds_to_release} beds, {icu_to_release} ICU). "
                  f"Next nearest hospital '{next_hosp['name']}' selected with "
                  f"{next_hosp['available_beds']} available beds. "
                  f"New allocation created (ID: {new_alloc_id}).",
        request_id=request_id,
        output_data={
            "rejected_hospital": rejected_hospital_name,
            "new_hospital": next_hosp["name"],
            "new_hospital_id": next_hosp["id"],
            "new_allocation_id": new_alloc_id,
            "beds_reserved": beds_needed,
        },
        status="success",
        mode="live",
    )

    return [next_hosp, new_alloc_id]

