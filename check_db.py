import sys
sys.path.insert(0, '.')
from database.db_manager import initialize_database, fetch_all

initialize_database()

hospitals  = fetch_all("SELECT id, name FROM hospitals")
ambulances = fetch_all("SELECT id, vehicle_number FROM ambulances")
resources  = fetch_all("SELECT id, name, resource_type FROM resources")
disasters  = fetch_all("SELECT id, name, status FROM disasters")
roads      = fetch_all("SELECT COUNT(*) as cnt FROM roads")
requests   = fetch_all("SELECT COUNT(*) as cnt FROM emergency_requests")

print(f"Hospitals:  {len(hospitals)}")
print(f"Ambulances: {len(ambulances)}")
print(f"Resources:  {len(resources)}")
print(f"Disasters:  {len(disasters)}")
road_cnt = roads[0]["cnt"] if roads else 0
req_cnt  = requests[0]["cnt"] if requests else 0
print(f"Roads:      {road_cnt}")
print(f"Requests:   {req_cnt}")

for h in hospitals[:3]:
    print(f"  Hospital:  {h['id']} - {h['name']}")
for a in ambulances[:3]:
    print(f"  Ambulance: {a['id']} - {a['vehicle_number']}")
for r in resources[:3]:
    print(f"  Resource:  {r['id']} - {r['name']} ({r['resource_type']})")
for d in disasters:
    print(f"  Disaster:  {d['id']} - {d['name']} [{d['status']}]")
