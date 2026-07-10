"""
ResQNet AI - Seed Data
Preloads Chennai Flood disaster scenario with realistic data:
  - 5 hospitals (varied capacities)
  - 10 ambulances
  - 3 rescue boats
  - 2 fire stations
  - 15 blocked roads
  - 50 emergency requests
  - 8 emergency shelters
"""

import json
import random
from datetime import datetime, timedelta
from database.db_manager import (
    initialize_database, execute_write, execute_many,
    is_database_seeded, fetch_all
)

# ── Randomization seed for reproducibility ────────────────────────────────────
random.seed(42)

# ── Chennai coordinates helpers ───────────────────────────────────────────────
def rand_chennai_coord(lat_c: float, lon_c: float, spread: float = 0.04):
    return (round(lat_c + random.uniform(-spread, spread), 6),
            round(lon_c + random.uniform(-spread, spread), 6))


# ══════════════════════════════════════════════════════════════════════════════
# HOSPITALS  (5 real Chennai hospitals)
# ══════════════════════════════════════════════════════════════════════════════
HOSPITALS = [
    {
        "name": "Apollo Hospitals - Greams Road",
        "address": "21, Greams Lane, Off Greams Road, Chennai - 600006",
        "latitude": 13.0564, "longitude": 80.2496,
        "total_beds": 500, "available_beds": 120,
        "total_icu": 50,  "available_icu": 12,
        "total_doctors": 80, "available_doctors": 20,
        "status": "Operational",
        "specializations": json.dumps(["Trauma", "Cardiology", "Neurology", "Burns"]),
        "contact_phone": "+91-44-2829-3333",
    },
    {
        "name": "Fortis Malar Hospital - Adyar",
        "address": "52, 1st Main Road, Gandhi Nagar, Adyar, Chennai - 600020",
        "latitude": 13.0067, "longitude": 80.2206,
        "total_beds": 180, "available_beds": 45,
        "total_icu": 20,  "available_icu": 5,
        "total_doctors": 35, "available_doctors": 8,
        "status": "Operational",
        "specializations": json.dumps(["Orthopaedics", "Cardiology", "Trauma"]),
        "contact_phone": "+91-44-4289-2222",
    },
    {
        "name": "MIOT International - Manapakkam",
        "address": "4/112, Mount Poonamallee Road, Manapakkam, Chennai - 600089",
        "latitude": 13.0115, "longitude": 80.1874,
        "total_beds": 350, "available_beds": 85,
        "total_icu": 35,  "available_icu": 8,
        "total_doctors": 60, "available_doctors": 14,
        "status": "Operational",
        "specializations": json.dumps(["Orthopaedics", "Trauma", "Spine", "Neurology"]),
        "contact_phone": "+91-44-2249-7777",
    },
    {
        "name": "Government General Hospital - Park Town",
        "address": "Park Town, Chennai - 600003",
        "latitude": 13.0847, "longitude": 80.2785,
        "total_beds": 1000, "available_beds": 210,
        "total_icu": 80,  "available_icu": 18,
        "total_doctors": 150, "available_doctors": 38,
        "status": "Operational",
        "specializations": json.dumps(["Emergency", "General Surgery", "Trauma", "Burn", "Paediatrics"]),
        "contact_phone": "+91-44-2530-5000",
    },
    {
        "name": "Sri Ramachandra Medical Centre - Porur",
        "address": "No.1, Ramachandra Nagar, Porur, Chennai - 600116",
        "latitude": 13.0339, "longitude": 80.1620,
        "total_beds": 400, "available_beds": 95,
        "total_icu": 40,  "available_icu": 10,
        "total_doctors": 70, "available_doctors": 16,
        "status": "Operational",
        "specializations": json.dumps(["Trauma", "Cardiology", "Neurology", "Multi-Speciality"]),
        "contact_phone": "+91-44-4592-8888",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# AMBULANCES  (10 vehicles)
# ══════════════════════════════════════════════════════════════════════════════
AMBULANCE_DRIVERS = [
    ("Rajesh Kumar",   "+91-98410-11111"),
    ("Selvam P",       "+91-98420-22222"),
    ("Murugesan T",    "+91-98430-33333"),
    ("Arjun Nair",     "+91-98440-44444"),
    ("Priya Suresh",   "+91-98450-55555"),
    ("Karthik Vel",    "+91-98460-66666"),
    ("Divya R",        "+91-98470-77777"),
    ("Senthil Kumar",  "+91-98480-88888"),
    ("Vijay M",        "+91-98490-99999"),
    ("Lakshmi Devi",   "+91-98400-10101"),
]

AMBULANCE_LOCATIONS = [
    (13.0827, 80.2707),   # City Center
    (13.0564, 80.2496),   # Near Apollo
    (13.0067, 80.2206),   # Near Fortis Malar
    (13.0847, 80.2785),   # Near GGH
    (13.0339, 80.1620),   # Near Sri Ramachandra
    (13.0630, 80.2500),   # Egmore
    (13.0500, 80.2100),   # T Nagar
    (13.1100, 80.2900),   # Perambur
    (13.0200, 80.2700),   # Mylapore
    (13.0700, 80.2400),   # Anna Nagar
]

AMBULANCES = []
for i, (driver, phone) in enumerate(AMBULANCE_DRIVERS):
    lat, lon = AMBULANCE_LOCATIONS[i]
    status = "Available" if i < 6 else "Dispatched"
    AMBULANCES.append({
        "vehicle_number": f"TN-09-AM-{1001 + i:04d}",
        "driver_name": driver,
        "driver_phone": phone,
        "latitude": lat,
        "longitude": lon,
        "status": status,
        "fuel_level": random.randint(60, 100),
    })

# ══════════════════════════════════════════════════════════════════════════════
# RESOURCES  (boats, fire trucks, rescue teams)
# ══════════════════════════════════════════════════════════════════════════════
RESOURCES = [
    # Rescue Boats (3)
    {
        "name": "Rescue Boat Alpha",
        "resource_type": "Rescue Boat",
        "location_name": "Marina Beach Coast Guard Station",
        "latitude": 13.0525, "longitude": 80.2821,
        "status": "Available", "capacity": 12,
        "operator_name": "Coast Guard Team A",
        "operator_phone": "+91-44-2345-6780",
    },
    {
        "name": "Rescue Boat Bravo",
        "resource_type": "Rescue Boat",
        "location_name": "Adyar River Rescue Base",
        "latitude": 13.0050, "longitude": 80.2560,
        "status": "Deployed", "capacity": 8,
        "operator_name": "NDRF Team B",
        "operator_phone": "+91-44-2345-6781",
    },
    {
        "name": "Rescue Boat Charlie",
        "resource_type": "Rescue Boat",
        "location_name": "Cooum River Station",
        "latitude": 13.0700, "longitude": 80.2600,
        "status": "Available", "capacity": 10,
        "operator_name": "SDRF Team C",
        "operator_phone": "+91-44-2345-6782",
    },
    # Fire Trucks / Fire Stations (2)
    {
        "name": "Fire Engine TN-01 (Egmore Station)",
        "resource_type": "Fire Truck",
        "location_name": "Egmore Fire Station",
        "latitude": 13.0780, "longitude": 80.2622,
        "status": "Available", "capacity": 6,
        "operator_name": "Fire Officer Ramesh",
        "operator_phone": "+91-44-2819-0101",
    },
    {
        "name": "Fire Engine TN-02 (Adyar Station)",
        "resource_type": "Fire Truck",
        "location_name": "Adyar Fire Station",
        "latitude": 13.0100, "longitude": 80.2580,
        "status": "Available", "capacity": 6,
        "operator_name": "Fire Officer Suresh",
        "operator_phone": "+91-44-2441-0202",
    },
    # Rescue Teams (NDRF/SDRF)
    {
        "name": "NDRF Team 1 - Chennai",
        "resource_type": "Rescue Team",
        "location_name": "NDRF Staging Area - Jawaharlal Nehru Stadium",
        "latitude": 13.0604, "longitude": 80.2495,
        "status": "Available", "capacity": 25,
        "operator_name": "Commander Vijay Singh",
        "operator_phone": "+91-44-2819-0303",
    },
    {
        "name": "SDRF Team 2 - Tamil Nadu",
        "resource_type": "Rescue Team",
        "location_name": "SDRF Base - Velachery",
        "latitude": 12.9810, "longitude": 80.2209,
        "status": "Deployed", "capacity": 20,
        "operator_name": "Commander Anand R",
        "operator_phone": "+91-44-2450-0404",
    },
    {
        "name": "NDRF Team 3 - Rapid Response",
        "resource_type": "Rescue Team",
        "location_name": "NDRF Forward Base - Tambaram",
        "latitude": 12.9229, "longitude": 80.1275,
        "status": "Available", "capacity": 30,
        "operator_name": "Commander Pradeep S",
        "operator_phone": "+91-44-2226-0505",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# DISASTERS  (Chennai Flood - main scenario)
# ══════════════════════════════════════════════════════════════════════════════
DISASTERS = [
    {
        "name": "Chennai Flood 2025 - Northeast Monsoon Surge",
        "disaster_type": "Flood",
        "severity": 4,
        "latitude": 13.0827,
        "longitude": 80.2707,
        "affected_radius_km": 18.0,
        "affected_people": 125000,
        "description": (
            "Severe flooding caused by heavy northeast monsoon rainfall in Chennai. "
            "Adyar and Cooum rivers have overflowed. Low-lying areas including Velachery, "
            "Tambaram, Perumbakkam, and parts of Anna Nagar are severely inundated. "
            "Multiple road closures reported. Rescue operations ongoing."
        ),
        "status": "Active",
    }
]

# ══════════════════════════════════════════════════════════════════════════════
# BLOCKED ROADS  (15 road closures)
# ══════════════════════════════════════════════════════════════════════════════
BLOCKED_ROADS = [
    {
        "road_name": "Anna Salai (Mount Road)",
        "from_location": "Gemini Flyover", "to_location": "Thousand Lights",
        "from_lat": 13.0609, "from_lon": 80.2500,
        "to_lat": 13.0540, "to_lon": 80.2527,
        "condition": "Flooded", "blockage_reason": "Heavy flooding - 1.5m water level",
        "severity": 4, "is_passable": 0,
    },
    {
        "road_name": "Rajiv Gandhi Salai (IT Expressway)",
        "from_location": "Sholinganallur", "to_location": "Perungudi",
        "from_lat": 12.9010, "from_lon": 80.2273,
        "to_lat": 12.9367, "to_lon": 80.2206,
        "condition": "Flooded", "blockage_reason": "IT corridor waterlogged - 0.8m depth",
        "severity": 3, "is_passable": 0,
    },
    {
        "road_name": "ECR - East Coast Road",
        "from_location": "Thiruvanmiyur", "to_location": "Palavakkam",
        "from_lat": 12.9820, "from_lon": 80.2567,
        "to_lat": 12.9720, "to_lon": 80.2621,
        "condition": "Flooded", "blockage_reason": "Coastal surge flooding - 2m water level",
        "severity": 5, "is_passable": 0,
    },
    {
        "road_name": "Velachery Main Road",
        "from_location": "Velachery Junction", "to_location": "Taramani",
        "from_lat": 12.9786, "from_lon": 80.2209,
        "to_lat": 12.9845, "to_lon": 80.2401,
        "condition": "Flooded", "blockage_reason": "Stormwater drain overflow - 1.2m depth",
        "severity": 4, "is_passable": 0,
    },
    {
        "road_name": "Adyar Bridge",
        "from_location": "Adyar", "to_location": "Besant Nagar",
        "from_lat": 13.0067, "from_lon": 80.2508,
        "to_lat": 12.9990, "to_lon": 80.2650,
        "condition": "Collapsed", "blockage_reason": "Bridge partially damaged by flood surge",
        "severity": 5, "is_passable": 0,
    },
    {
        "road_name": "100 Feet Road - Vadapalani",
        "from_location": "Vadapalani", "to_location": "Ashok Nagar",
        "from_lat": 13.0525, "from_lon": 80.2115,
        "to_lat": 13.0480, "to_lon": 80.2001,
        "condition": "Blocked", "blockage_reason": "Fallen trees blocking road",
        "severity": 3, "is_passable": 0,
    },
    {
        "road_name": "Perambur Barracks Road",
        "from_location": "Perambur", "to_location": "Otteri",
        "from_lat": 13.1098, "from_lon": 80.2599,
        "to_lat": 13.1001, "to_lon": 80.2534,
        "condition": "Flooded", "blockage_reason": "Cooum river overflow",
        "severity": 3, "is_passable": 0,
    },
    {
        "road_name": "GST Road - Chrompet",
        "from_location": "Chrompet", "to_location": "Pallavaram",
        "from_lat": 12.9518, "from_lon": 80.1450,
        "to_lat": 12.9667, "to_lon": 80.1495,
        "condition": "Flooded", "blockage_reason": "Low-lying area submerged",
        "severity": 4, "is_passable": 0,
    },
    {
        "road_name": "Poonamallee High Road",
        "from_location": "Poonamallee", "to_location": "Koyambedu",
        "from_lat": 13.0490, "from_lon": 80.1174,
        "to_lat": 13.0693, "to_lon": 80.1942,
        "condition": "Blocked", "blockage_reason": "Debris and waterlogging",
        "severity": 2, "is_passable": 0,
    },
    {
        "road_name": "Taramani Link Road",
        "from_location": "IIT Madras Gate", "to_location": "Taramani",
        "from_lat": 12.9916, "from_lon": 80.2336,
        "to_lat": 12.9845, "to_lon": 80.2401,
        "condition": "Flooded", "blockage_reason": "IIT lake overflow",
        "severity": 4, "is_passable": 0,
    },
    {
        "road_name": "Medavakkam - OMR Junction",
        "from_location": "Medavakkam", "to_location": "Sholinganallur",
        "from_lat": 12.9219, "from_lon": 80.1981,
        "to_lat": 12.9010, "to_lon": 80.2273,
        "condition": "Flooded", "blockage_reason": "Extensive waterlogging",
        "severity": 3, "is_passable": 0,
    },
    {
        "road_name": "Saidapet Bridge",
        "from_location": "Saidapet", "to_location": "St Thomas Mount",
        "from_lat": 13.0232, "from_lon": 80.2230,
        "to_lat": 13.0136, "to_lon": 80.2042,
        "condition": "Damaged", "blockage_reason": "Structural damage - weight limit imposed",
        "severity": 4, "is_passable": 0,
    },
    {
        "road_name": "Coats Road - Perumbakkam",
        "from_location": "Perumbakkam", "to_location": "Sholinganallur",
        "from_lat": 12.9100, "from_lon": 80.2050,
        "to_lat": 12.9010, "to_lon": 80.2273,
        "condition": "Flooded", "blockage_reason": "Lake overflow from Perumbakkam Lake",
        "severity": 5, "is_passable": 0,
    },
    {
        "road_name": "Ambattur Industrial Estate Road",
        "from_location": "Ambattur OT", "to_location": "Padi",
        "from_lat": 13.1109, "from_lon": 80.1628,
        "to_lat": 13.1191, "to_lon": 80.2051,
        "condition": "Blocked", "blockage_reason": "Industrial area flooding - chemical risk",
        "severity": 3, "is_passable": 0,
    },
    {
        "road_name": "Nungambakkam High Road",
        "from_location": "Nungambakkam", "to_location": "Egmore",
        "from_lat": 13.0604, "from_lon": 80.2438,
        "to_lat": 13.0780, "to_lon": 80.2622,
        "condition": "Flooded", "blockage_reason": "Urban flooding - stormwater overflow",
        "severity": 2, "is_passable": 0,
    },
]

# ── Clear (passable) roads for routing ────────────────────────────────────────
CLEAR_ROADS = [
    {
        "road_name": "NH 48 (Chennai-Bangalore Highway)",
        "from_location": "Ambattur", "to_location": "Poonamallee",
        "from_lat": 13.1109, "from_lon": 80.1628,
        "to_lat": 13.0490, "to_lon": 80.1174,
        "condition": "Clear", "blockage_reason": None, "severity": 0, "is_passable": 1,
    },
    {
        "road_name": "Inner Ring Road",
        "from_location": "Koyambedu", "to_location": "Madhavaram",
        "from_lat": 13.0693, "from_lon": 80.1942,
        "to_lat": 13.1485, "to_lon": 80.2397,
        "condition": "Clear", "blockage_reason": None, "severity": 0, "is_passable": 1,
    },
    {
        "road_name": "Old Mahabalipuram Road (OMR) - North Section",
        "from_location": "Perungudi", "to_location": "Siruseri",
        "from_lat": 12.9367, "from_lon": 80.2206,
        "to_lat": 12.8390, "to_lon": 80.2288,
        "condition": "Clear", "blockage_reason": None, "severity": 0, "is_passable": 1,
    },
    {
        "road_name": "EVR Periyar Salai",
        "from_location": "Koyambedu", "to_location": "Egmore",
        "from_lat": 13.0693, "from_lon": 80.1942,
        "to_lat": 13.0780, "to_lon": 80.2622,
        "condition": "Clear", "blockage_reason": None, "severity": 0, "is_passable": 1,
    },
    {
        "road_name": "Jawaharlal Nehru Salai",
        "from_location": "Anna Nagar", "to_location": "Koyambedu",
        "from_lat": 13.0870, "from_lon": 80.2101,
        "to_lat": 13.0693, "to_lon": 80.1942,
        "condition": "Clear", "blockage_reason": None, "severity": 0, "is_passable": 1,
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# EMERGENCY REQUESTS  (50 citizen reports)
# ══════════════════════════════════════════════════════════════════════════════
CITIZEN_NAMES = [
    "Arjun Sharma", "Priya Krishnan", "Murugan S", "Anitha R", "Venkatesh T",
    "Kavitha M", "Sathish K", "Deepa N", "Ramesh V", "Sunita L",
    "Balaji P", "Meena C", "Gopi A", "Revathi S", "Suresh J",
    "Nithya R", "Chandran P", "Suganya M", "Dinesh K", "Bhavani A",
    "Karthick S", "Uma D", "Selvakumar N", "Jayanthi P", "Arun M",
    "Hema L", "Vasanth R", "Pooja K", "Manikandan T", "Rani S",
    "Vinoth A", "Lakshmi P", "Tamilselvan B", "Saranya C", "Praveen G",
    "Dharani K", "Saravanan M", "Geetha L", "Sugumar T", "Archana N",
    "Ezhilarasan K", "Vimala R", "Naveen S", "Priya B", "Muthukumar C",
    "Nandha R", "Sowmya V", "Kiran T", "Lalitha P", "Senthilnathan A"
]

DISASTER_DESCRIPTIONS = [
    "Water level reaching 4 feet in our house, {n} people including elderly and children trapped",
    "Our street is completely flooded, {n} families need immediate evacuation",
    "Elderly person with heart condition - ambulance needed urgently, flood water rising",
    "Collapsed wall injured {n} people, medical assistance required",
    "Snake bite during flooding - need immediate medical help for {n} person",
    "Trapped on rooftop with {n} family members - boat needed for rescue",
    "Pregnant woman in labor - unable to reach hospital due to flooding",
    "{n} people including wheelchair user stranded - require special assistance",
    "Gas cylinder explosion during flood - {n} injured, burns and smoke inhalation",
    "Children separated from parents in flood - {n} kids need shelter",
    "Diabetic patient without medication for 2 days - blood sugar critical - {n} people",
    "Water contamination - 50+ people showing diarrhoea symptoms in our area",
    "Elderly couple with no food or water for 36 hours - stranded in {n}-story building",
    "Basement parking flooded - {n} vehicles trapped, people stuck inside garage",
    "Building partially collapsed - {n} people may be trapped under debris",
    "Rescue needed - {n} workers trapped in flooded factory",
    "Child with high fever and no access to medicine or hospital",
    "Community of {n} people with no shelter - requesting relocation to relief camp",
    "Electric line down in flood water - dangerous situation - {n} people nearby",
    "Boat capsized - {n} people struggling to swim - rescue needed immediately",
]

REQUEST_LOCATIONS = [
    ("Velachery", 12.9786, 80.2209),
    ("Tambaram", 12.9229, 80.1275),
    ("Perumbakkam", 12.9100, 80.2050),
    ("Sholinganallur", 12.9010, 80.2273),
    ("Adyar", 13.0067, 80.2508),
    ("Besant Nagar", 12.9990, 80.2650),
    ("Anna Nagar", 13.0870, 80.2101),
    ("Nungambakkam", 13.0604, 80.2438),
    ("Egmore", 13.0780, 80.2622),
    ("Perambur", 13.1098, 80.2599),
    ("Madipakkam", 12.9560, 80.2098),
    ("Pallavaram", 12.9667, 80.1495),
    ("Chrompet", 12.9518, 80.1450),
    ("T Nagar", 13.0500, 80.2100),
    ("Kodambakkam", 13.0520, 80.2231),
    ("Saidapet", 13.0232, 80.2230),
    ("Mylapore", 13.0200, 80.2700),
    ("Thiruvanmiyur", 12.9820, 80.2567),
    ("Villivakkam", 13.1098, 80.2141),
    ("Tondiarpet", 13.1200, 80.2800),
    ("Royapuram", 13.1100, 80.2950),
    ("Tiruvottiyur", 13.1600, 80.3000),
    ("Puzhal", 13.1500, 80.2000),
    ("Avadi", 13.1150, 80.0948),
    ("Porur", 13.0339, 80.1620),
]

STATUSES = ["Pending", "Processing", "Dispatched", "Resolved"]
STATUS_WEIGHTS = [0.30, 0.20, 0.25, 0.25]


def build_emergency_requests(disaster_id: int) -> list:
    requests = []
    for i in range(50):
        name = CITIZEN_NAMES[i]
        loc_name, lat, lon = random.choice(REQUEST_LOCATIONS)
        lat += random.uniform(-0.015, 0.015)
        lon += random.uniform(-0.015, 0.015)
        n_people = random.randint(1, 12)
        desc_template = random.choice(DISASTER_DESCRIPTIONS)
        desc = desc_template.format(n=n_people)
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        severity = random.randint(1, 5)
        phone = f"+91-{random.randint(6000000000, 9999999999)}"

        # Assign hospitals to dispatched/resolved
        hosp_id = None
        amb_id = None
        if status in ("Dispatched", "Resolved"):
            hosp_id = random.randint(1, 5)
            amb_id = random.randint(1, 10)

        requests.append({
            "citizen_name": name,
            "citizen_phone": phone,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "address": f"{loc_name}, Chennai",
            "description": desc,
            "disaster_type": "Flood",
            "severity": severity,
            "num_people": n_people,
            "status": status,
            "disaster_id": disaster_id,
            "assigned_hospital_id": hosp_id,
            "assigned_ambulance_id": amb_id,
        })
    return requests


# ══════════════════════════════════════════════════════════════════════════════
# SHELTERS
# ══════════════════════════════════════════════════════════════════════════════
SHELTERS = [
    {
        "name": "Jawaharlal Nehru Indoor Stadium",
        "address": "Sydenhams Road, Anna Salai, Chennai - 600002",
        "latitude": 13.0604, "longitude": 80.2495,
        "capacity": 5000, "current_occupancy": 3200, "status": "Active",
        "contact_person": "District Collector Office - +91-44-2538-1720",
    },
    {
        "name": "Anna University - Velachery Campus",
        "address": "Sardar Patel Road, Guindy, Chennai - 600025",
        "latitude": 13.0116, "longitude": 80.2337,
        "capacity": 2000, "current_occupancy": 1800, "status": "Active",
        "contact_person": "Relief Coordinator - +91-44-2235-0305",
    },
    {
        "name": "Tambaram Corporation School",
        "address": "GST Road, Tambaram, Chennai - 600045",
        "latitude": 12.9229, "longitude": 80.1275,
        "capacity": 1500, "current_occupancy": 950, "status": "Active",
        "contact_person": "Tambaram Municipality - +91-44-2226-5511",
    },
    {
        "name": "Perambur Government School",
        "address": "Barracks Road, Perambur, Chennai - 600011",
        "latitude": 13.1098, "longitude": 80.2599,
        "capacity": 1000, "current_occupancy": 620, "status": "Active",
        "contact_person": "Zone Relief Camp - +91-44-2651-0101",
    },
    {
        "name": "Sholinganallur Government Polytechnic",
        "address": "OMR, Sholinganallur, Chennai - 600119",
        "latitude": 12.9010, "longitude": 80.2273,
        "capacity": 800, "current_occupancy": 790, "status": "Active",
        "contact_person": "IT Corridor Relief - +91-44-2450-2020",
    },
    {
        "name": "Adyar Community Hall",
        "address": "Gandhi Nagar, Adyar, Chennai - 600020",
        "latitude": 13.0067, "longitude": 80.2206,
        "capacity": 600, "current_occupancy": 580, "status": "Active",
        "contact_person": "Adyar RWA - +91-44-2441-5050",
    },
    {
        "name": "YMCA - Nandanam",
        "address": "Nandanam, Chennai - 600035",
        "latitude": 13.0281, "longitude": 80.2351,
        "capacity": 400, "current_occupancy": 310, "status": "Active",
        "contact_person": "YMCA Relief - +91-44-2432-1234",
    },
    {
        "name": "Porur Rajalakshmi Engineering College",
        "address": "GST Road, Porur, Chennai - 600116",
        "latitude": 13.0339, "longitude": 80.1620,
        "capacity": 3000, "current_occupancy": 1200, "status": "Active",
        "contact_person": "College Relief - +91-44-2249-0606",
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SEED FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def seed_all():
    """Populate the database with the Chennai flood scenario."""
    print("[SEED] Starting data seeding...")

    # ── Hospitals ──────────────────────────────────────────────────────────────
    for h in HOSPITALS:
        execute_write(
            """INSERT INTO hospitals
               (name, address, latitude, longitude, total_beds, available_beds,
                total_icu, available_icu, total_doctors, available_doctors,
                status, specializations, contact_phone)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (h["name"], h["address"], h["latitude"], h["longitude"],
             h["total_beds"], h["available_beds"], h["total_icu"], h["available_icu"],
             h["total_doctors"], h["available_doctors"], h["status"],
             h["specializations"], h["contact_phone"])
        )
    print(f"[SEED] [OK] Inserted {len(HOSPITALS)} hospitals")

    # ── Ambulances ─────────────────────────────────────────────────────────────
    for a in AMBULANCES:
        execute_write(
            """INSERT INTO ambulances
               (vehicle_number, driver_name, driver_phone, latitude, longitude, status, fuel_level)
               VALUES (?,?,?,?,?,?,?)""",
            (a["vehicle_number"], a["driver_name"], a["driver_phone"],
             a["latitude"], a["longitude"], a["status"], a["fuel_level"])
        )
    print(f"[SEED] [OK] Inserted {len(AMBULANCES)} ambulances")

    # ── Disasters ──────────────────────────────────────────────────────────────
    disaster_id = None
    for d in DISASTERS:
        disaster_id = execute_write(
            """INSERT INTO disasters
               (name, disaster_type, severity, latitude, longitude,
                affected_radius_km, affected_people, description, status)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (d["name"], d["disaster_type"], d["severity"],
             d["latitude"], d["longitude"], d["affected_radius_km"],
             d["affected_people"], d["description"], d["status"])
        )
    print(f"[SEED] [OK] Inserted {len(DISASTERS)} disaster(s), main ID={disaster_id}")

    # ── Resources ──────────────────────────────────────────────────────────────
    for r in RESOURCES:
        execute_write(
            """INSERT INTO resources
               (name, resource_type, location_name, latitude, longitude,
                status, capacity, operator_name, operator_phone)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (r["name"], r["resource_type"], r["location_name"],
             r["latitude"], r["longitude"], r["status"], r["capacity"],
             r["operator_name"], r["operator_phone"])
        )
    print(f"[SEED] [OK] Inserted {len(RESOURCES)} resources")

    # ── Roads (blocked + clear) ────────────────────────────────────────────────
    all_roads = BLOCKED_ROADS + CLEAR_ROADS
    for rd in all_roads:
        execute_write(
            """INSERT INTO roads
               (road_name, from_location, to_location, from_lat, from_lon,
                to_lat, to_lon, condition, blockage_reason, severity, is_passable)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (rd["road_name"], rd["from_location"], rd["to_location"],
             rd["from_lat"], rd["from_lon"], rd["to_lat"], rd["to_lon"],
             rd["condition"], rd.get("blockage_reason"), rd["severity"], rd["is_passable"])
        )
    print(f"[SEED] [OK] Inserted {len(all_roads)} roads ({len(BLOCKED_ROADS)} blocked, {len(CLEAR_ROADS)} clear)")

    # ── Emergency Requests ─────────────────────────────────────────────────────
    if disaster_id:
        requests = build_emergency_requests(disaster_id)
        for req in requests:
            execute_write(
                """INSERT INTO emergency_requests
                   (citizen_name, citizen_phone, latitude, longitude, address,
                    description, disaster_type, severity, num_people, status,
                    disaster_id, assigned_hospital_id, assigned_ambulance_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (req["citizen_name"], req["citizen_phone"], req["latitude"],
                 req["longitude"], req["address"], req["description"],
                 req["disaster_type"], req["severity"], req["num_people"],
                 req["status"], req["disaster_id"],
                 req["assigned_hospital_id"], req["assigned_ambulance_id"])
            )
        print(f"[SEED] [OK] Inserted {len(requests)} emergency requests")

    # ── Shelters ───────────────────────────────────────────────────────────────
    for s in SHELTERS:
        execute_write(
            """INSERT INTO shelters
               (name, address, latitude, longitude, capacity, current_occupancy, status, contact_person)
               VALUES (?,?,?,?,?,?,?,?)""",
            (s["name"], s["address"], s["latitude"], s["longitude"],
             s["capacity"], s["current_occupancy"], s["status"], s["contact_person"])
        )
    print(f"[SEED] [OK] Inserted {len(SHELTERS)} shelters")

    # ── Default users ──────────────────────────────────────────────────────────
    users = [
        ("Admin User",     "+91-00000-00001", "admin@resqnet.ai",     "admin",    None),
        ("Gov Official",   "+91-00000-00002", "gov@resqnet.ai",       "government", None),
        ("Hospital Admin", "+91-00000-00003", "hospital@resqnet.ai",  "hospital_staff", 1),
        ("Ambulance 1",    "+91-98410-11111", "amb1@resqnet.ai",      "ambulance_driver", 1),
        ("Citizen Demo",   "+91-00000-00005", "citizen@resqnet.ai",   "citizen",  None),
    ]
    for u in users:
        execute_write(
            """INSERT OR IGNORE INTO users
               (name, phone, email, role, linked_entity_id)
               VALUES (?,?,?,?,?)""",
            u
        )
    print(f"[SEED] [OK] Inserted {len(users)} default users")

    print("\n[SEED] [DONE] Chennai Flood scenario seeded successfully!")
    print("[SEED] Summary:")
    print(f"       Hospitals        : {len(HOSPITALS)}")
    print(f"       Ambulances       : {len(AMBULANCES)}")
    print(f"       Resources        : {len(RESOURCES)}")
    print(f"       Disasters        : {len(DISASTERS)}")
    print(f"       Roads (total)    : {len(all_roads)}")
    print(f"       Emergency Requests: 50")
    print(f"       Shelters         : {len(SHELTERS)}")


def run_seed():
    """Entry point: initialize DB and seed if needed."""
    initialize_database()
    if not is_database_seeded():
        seed_all()
    else:
        print("[SEED] Database already seeded - skipping.")


if __name__ == "__main__":
    run_seed()
