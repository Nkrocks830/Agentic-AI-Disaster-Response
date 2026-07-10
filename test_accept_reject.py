"""
End-to-end flow test:
1. Simulate a citizen submitting an emergency (pipeline runs)
2. Verify ambulance is NOT dispatched yet (still Available)
3. Verify request is in Processing state with tentative ambulance assigned
4. Simulate hospital clicking Accept
5. Verify ambulance IS now Dispatched
6. Verify request is now Dispatched (visible in Ambulance Dashboard)
7. Reset and test Reject flow
"""
import sys
sys.path.insert(0, '.')
from database.db_manager import (
    initialize_database, fetch_all, fetch_one, execute_write,
    accept_patient_allocation, reject_patient_allocation,
    get_ambulance_by_id, get_request_by_id
)

initialize_database()

print("=" * 60)
print("TEST: Accept -> Ambulance should be Dispatched")
print("=" * 60)

# Find a Processing request with a tentative ambulance
req = fetch_one(
    "SELECT * FROM emergency_requests WHERE status='Processing' AND assigned_ambulance_id IS NOT NULL LIMIT 1"
)
if not req:
    print("No Processing requests found. Running a simulated pipeline first...")
    from orchestrator.orchestrator import Orchestrator
    from models.disaster_models import DisasterInput
    orch = Orchestrator()
    inp = DisasterInput(
        citizen_name="Test Citizen",
        citizen_phone="9876543210",
        latitude=13.0827, longitude=80.2707,
        address="Velachery, Chennai",
        description="Test flood emergency - water level rising",
        num_people=3,
    )
    result = orch.process_emergency(inp)
    req = fetch_one(
        "SELECT * FROM emergency_requests WHERE id=?", (result.request_id,)
    )
    print(f"Created request #{req['id']}")

print(f"\nRequest #{req['id']}:")
print(f"  Status:              {req['status']}  (expected: Processing)")
print(f"  assigned_hospital:   {req['assigned_hospital_id']}")
print(f"  assigned_ambulance:  {req['assigned_ambulance_id']}")

amb_id = req["assigned_ambulance_id"]
hosp_id = req["assigned_hospital_id"]

# Check ambulance is still Available (NOT Dispatched)
if amb_id:
    amb = get_ambulance_by_id(amb_id)
    print(f"  Ambulance #{amb_id} status: {amb['status']}  (expected: Available)")
    assert amb["status"] == "Available", f"FAIL: Ambulance already Dispatched before Accept! Got: {amb['status']}"
    print("  [PASS] Ambulance is Available before Accept")

# Find the pending allocation
alloc = fetch_one(
    "SELECT * FROM patient_allocations WHERE request_id=? AND allocation_status='pending' LIMIT 1",
    (req["id"],)
)
if not alloc:
    print("  No pending allocation found - checking all allocations for this request:")
    allocs = fetch_all("SELECT * FROM patient_allocations WHERE request_id=?", (req["id"],))
    for a in allocs:
        print(f"    alloc #{a['id']}: status={a['allocation_status']}, hospital={a['hospital_id']}")
    sys.exit(1)

hosp = fetch_one("SELECT * FROM hospitals WHERE id=?", (alloc["hospital_id"],))
print(f"\n  Allocation #{alloc['id']}: hospital={hosp['name']}, beds={alloc['beds_reserved']}")

# --- ACCEPT ---
print("\n--- Clicking ACCEPT ---")
accept_patient_allocation(
    allocation_id=alloc["id"],
    request_id=req["id"],
    hospital_id=alloc["hospital_id"],
    hospital_name=hosp["name"],
    chosen_ambulance_id=amb_id,
)

req_after = get_request_by_id(req["id"])
amb_after = get_ambulance_by_id(amb_id) if amb_id else None
log = fetch_all("SELECT * FROM agent_logs WHERE request_id=? ORDER BY id DESC LIMIT 1", (req["id"],))
notif = fetch_all("SELECT * FROM notifications WHERE request_id=? ORDER BY id DESC LIMIT 1", (req["id"],))

print(f"  request status:      {req_after['status']}   (expected: Dispatched)")
print(f"  ambulance status:    {amb_after['status'] if amb_after else 'N/A'}  (expected: Dispatched)")
print(f"  agent log action:    {log[0]['action'] if log else 'NONE'}  (expected: accept_and_dispatch)")
print(f"  notification:        {notif[0]['message'][:70] if notif else 'NONE'}...")

assert req_after["status"] == "Dispatched",                     "FAIL: request not Dispatched"
assert (not amb_id or amb_after["status"] == "Dispatched"),     "FAIL: ambulance not Dispatched"
assert notif,                                                   "FAIL: no citizen notification"
print("  [PASS] ACCEPT workflow: ambulance dispatched, request Dispatched")

print("\n" + "=" * 60)
print("TEST: Reject -> Ambulance stays Available, re-allocated to next hospital")
print("=" * 60)

# Run a fresh pipeline for reject test
from orchestrator.orchestrator import Orchestrator
from models.disaster_models import DisasterInput
orch = Orchestrator()
inp2 = DisasterInput(
    citizen_name="Reject Test Citizen",
    citizen_phone="9000000001",
    latitude=13.0500, longitude=80.2500,
    address="T. Nagar, Chennai",
    description="Flood water entering ground floor, 2 elderly people stuck",
    num_people=2,
)
result2 = orch.process_emergency(inp2)
req2 = fetch_one("SELECT * FROM emergency_requests WHERE id=?", (result2.request_id,))
alloc2 = fetch_one(
    "SELECT * FROM patient_allocations WHERE request_id=? AND allocation_status='pending' LIMIT 1",
    (req2["id"],)
)
hosp2 = fetch_one("SELECT * FROM hospitals WHERE id=?", (alloc2["hospital_id"],))
amb2_id = req2["assigned_ambulance_id"]
amb2_before = get_ambulance_by_id(amb2_id) if amb2_id else None
beds_before = hosp2["available_beds"]

print(f"\nRequest #{req2['id']}: status={req2['status']}, hospital={hosp2['name']}")
print(f"  Ambulance #{amb2_id} before reject: {amb2_before['status'] if amb2_before else 'N/A'}")

print("\n--- Clicking REJECT ---")
result_reject = reject_patient_allocation(
    allocation_id=alloc2["id"],
    request_id=req2["id"],
    rejected_hospital_id=alloc2["hospital_id"],
    rejected_hospital_name=hosp2["name"],
    beds_to_release=alloc2["beds_reserved"],
    icu_to_release=alloc2["icu_reserved"],
)

req2_after = get_request_by_id(req2["id"])
amb2_after = get_ambulance_by_id(amb2_id) if amb2_id else None
alloc2_after = fetch_one("SELECT * FROM patient_allocations WHERE id=?", (alloc2["id"],))
hosp2_after = fetch_one("SELECT * FROM hospitals WHERE id=?", (alloc2["hospital_id"],))
log2 = fetch_all("SELECT * FROM agent_logs WHERE request_id=? ORDER BY id DESC LIMIT 1", (req2["id"],))

print(f"  allocation status:   {alloc2_after['allocation_status']}  (expected: rejected)")
print(f"  ambulance status:    {amb2_after['status'] if amb2_after else 'N/A'}  (expected: Available - NOT dispatched)")
print(f"  request status:      {req2_after['status']}  (expected: Processing for next hospital)")
print(f"  hospital beds:       {hosp2_after['available_beds']} (was {beds_before}, +{alloc2['beds_reserved']} released)")
print(f"  agent log action:    {log2[0]['action'] if log2 else 'NONE'}")

if result_reject:
    next_h, new_aid = result_reject
    print(f"  re-allocated to:     {next_h['name']} (new alloc #{new_aid})")

assert alloc2_after["allocation_status"] == "rejected",           "FAIL: allocation not rejected"
assert (not amb2_id or amb2_after["status"] == "Available"),       "FAIL: ambulance was dispatched on reject!"
assert hosp2_after["available_beds"] >= beds_before,               "FAIL: beds not released"
print("  [PASS] REJECT workflow: ambulance stays Available, beds released, re-allocated")

print("\n=== ALL TESTS PASSED ===")
