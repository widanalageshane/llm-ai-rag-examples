# create_heating_db.py
# MCP Day 6 - Exercise Option A: Create the House Heating System database
# Simulates a smart home heating system with rooms, heaters, and electricity spot prices
#
# Usage: python create_heating_db.py
# Output: heating.db (SQLite database)

import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = "heating.db"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"Removed existing {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Create Tables ──────────────────────────────────────────────

cursor.execute('''
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    floor INTEGER,
    area_sqm REAL,
    current_temp REAL,
    target_temp REAL,
    has_heater INTEGER DEFAULT 1
)''')

cursor.execute('''
CREATE TABLE heaters (
    id INTEGER PRIMARY KEY,
    room_id INTEGER REFERENCES rooms(id),
    model TEXT,
    power_watts INTEGER,
    status TEXT CHECK(status IN ('on', 'off', 'eco')),
    mode TEXT CHECK(mode IN ('manual', 'auto', 'schedule'))
)''')

cursor.execute('''
CREATE TABLE electricity_prices (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    price_cents_kwh REAL NOT NULL,
    source TEXT DEFAULT 'Nordpool'
)''')

cursor.execute('''
CREATE TABLE heating_log (
    id INTEGER PRIMARY KEY,
    room_id INTEGER REFERENCES rooms(id),
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT,
    price_at_time REAL
)''')

cursor.execute('''
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT
)''')

# ── Insert Sample Data ─────────────────────────────────────────

rooms = [
    (1, "Living Room",    1, 28.0, 21.5, 22.0, 1),
    (2, "Kitchen",        1, 14.0, 20.8, 21.0, 1),
    (3, "Master Bedroom", 2, 18.0, 19.2, 20.0, 1),
    (4, "Kids Room",      2, 12.0, 20.5, 21.0, 1),
    (5, "Bathroom",       1,  6.0, 23.0, 24.0, 1),
    (6, "Garage",         1, 30.0, 12.0, 10.0, 1),
    (7, "Hallway",        1, 10.0, 19.0, 19.0, 0),  # no heater
]

heaters = [
    (1, 1, "Adax Neo NP10",  1000, "on",  "auto"),
    (2, 1, "Adax Neo NP06",   600, "on",  "auto"),
    (3, 2, "Mill Invisible",   750, "on",  "auto"),
    (4, 3, "Adax Neo NP08",   800, "off", "schedule"),
    (5, 4, "Mill Invisible",   600, "on",  "auto"),
    (6, 5, "Ensto EPHBE",     500, "on",  "manual"),
    (7, 6, "Devi Devireg",   2000, "eco", "auto"),
]

# Generate 48 hours of electricity spot prices (hourly)
random.seed(42)
prices = []
base_time = datetime(2025, 1, 20, 0, 0, 0)
for i in range(48):
    t = base_time + timedelta(hours=i)
    hour = t.hour

    # Simulate realistic Nordpool pricing pattern (cents/kWh)
    # Night: cheap (2-6 cents), morning peak: expensive (8-15), day: moderate (5-10), evening peak: expensive (10-20)
    if 0 <= hour < 6:
        base_price = random.uniform(1.5, 4.0)
    elif 6 <= hour < 9:
        base_price = random.uniform(8.0, 15.0)
    elif 9 <= hour < 16:
        base_price = random.uniform(4.0, 9.0)
    elif 16 <= hour < 21:
        base_price = random.uniform(10.0, 22.0)
    else:
        base_price = random.uniform(3.0, 7.0)

    prices.append((i + 1, t.strftime("%Y-%m-%d %H:00:00"), round(base_price, 2), "Nordpool"))

# Generate some heating log entries
log_entries = [
    (1, 1, "2025-01-20 06:30:00", "heater_on",  "Morning warmup - auto schedule", 3.2),
    (2, 3, "2025-01-20 07:00:00", "heater_on",  "Bedroom schedule start",         8.5),
    (3, 6, "2025-01-20 08:00:00", "heater_eco", "Price spike > 10 cents",         12.1),
    (4, 1, "2025-01-20 17:00:00", "temp_boost", "User requested +2 degrees",      15.3),
    (5, 6, "2025-01-20 22:00:00", "heater_on",  "Price dropped below threshold",   4.8),
    (6, 4, "2025-01-20 21:00:00", "heater_on",  "Kids bedtime warmup",             6.2),
    (7, 1, "2025-01-21 06:15:00", "heater_on",  "Morning warmup - auto schedule",  2.8),
    (8, 5, "2025-01-21 06:30:00", "temp_boost", "Bathroom morning boost",          3.1),
]

settings_data = [
    ("max_price_threshold",  "12.0",  "Turn heaters to eco when price exceeds this (cents/kWh)"),
    ("night_mode_start",     "22:00", "Start of night mode (reduced temperatures)"),
    ("night_mode_end",       "06:00", "End of night mode"),
    ("night_temp_reduction", "2.0",   "Degrees to reduce during night mode"),
    ("eco_mode_reduction",   "3.0",   "Degrees to reduce in eco mode (high price)"),
    ("min_temp_any_room",    "15.0",  "Never let any room go below this temperature"),
]

cursor.executemany("INSERT INTO rooms VALUES (?,?,?,?,?,?,?)", rooms)
cursor.executemany("INSERT INTO heaters VALUES (?,?,?,?,?,?)", heaters)
cursor.executemany("INSERT INTO electricity_prices VALUES (?,?,?,?)", prices)
cursor.executemany("INSERT INTO heating_log VALUES (?,?,?,?,?,?)", log_entries)
cursor.executemany("INSERT INTO settings VALUES (?,?,?)", settings_data)

conn.commit()
conn.close()

print(f"Database created: {DB_PATH}")
print(f"  {len(rooms)} rooms")
print(f"  {len(heaters)} heaters")
print(f"  {len(prices)} hourly price records (48 hours)")
print(f"  {len(log_entries)} heating log entries")
print(f"  {len(settings_data)} system settings")
print()
print("Tables: rooms, heaters, electricity_prices, heating_log, settings")
print("Ready to use with your MCP server!")
