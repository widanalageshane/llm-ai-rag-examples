# exercise_solution_heating.py
# MCP Day 6 - Exercise Option A: SOLUTION
# House Heating System MCP Server — Complete Implementation
# ═══════════════════════════════════════════════════════════════

import sqlite3
import json
from datetime import datetime
from fastmcp import FastMCP

mcp = FastMCP("House Heating System")
DB_PATH = "heating.db"


def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════════════
#  RESOURCES
# ═══════════════════════════════════════════════════════════════

@mcp.resource("schema://heating/database")
def get_schema() -> str:
    """Database schema showing all tables and columns."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    schemas = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return "\n\n".join(schemas)


@mcp.resource("config://heating/settings")
def get_settings() -> str:
    """System settings including price thresholds and night mode config."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value, description FROM settings")
    settings = {row["key"]: {"value": row["value"], "description": row["description"]}
                for row in cursor.fetchall()}
    conn.close()
    return json.dumps(settings, indent=2)


@mcp.resource("data://prices/today")
def get_todays_prices() -> str:
    """Today's hourly electricity spot prices from Nordpool."""
    conn = get_db()
    cursor = conn.cursor()
    # Get the latest date in the data and show that day's prices
    cursor.execute("""
        SELECT timestamp, price_cents_kwh
        FROM electricity_prices
        ORDER BY timestamp DESC
        LIMIT 24
    """)
    prices = [{"time": row["timestamp"], "price_cents_kwh": row["price_cents_kwh"]}
              for row in cursor.fetchall()]
    conn.close()
    prices.reverse()  # Chronological order
    return json.dumps(prices, indent=2)


# ═══════════════════════════════════════════════════════════════
#  TOOL 1: Get Room Temperatures
# ═══════════════════════════════════════════════════════════════

@mcp.tool
def get_room_temperatures() -> str:
    """Get current temperatures for all rooms in the house.
    Shows each room's current temp, target temp, heater status, and
    whether the room is currently above or below its target.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.name AS room, r.floor, r.current_temp, r.target_temp,
               r.has_heater, h.status AS heater_status, h.power_watts
        FROM rooms r
        LEFT JOIN heaters h ON r.id = h.room_id
        ORDER BY r.floor, r.name
    """)
    rows = cursor.fetchall()
    conn.close()

    rooms = []
    for row in rows:
        diff = row["current_temp"] - row["target_temp"]
        if diff > 0.5:
            status = "above target"
        elif diff < -0.5:
            status = "BELOW target"
        else:
            status = "at target"

        rooms.append({
            "room": row["room"],
            "floor": row["floor"],
            "current_temp": row["current_temp"],
            "target_temp": row["target_temp"],
            "status": status,
            "heater": row["heater_status"] if row["has_heater"] else "no heater",
            "heater_power_watts": row["power_watts"] if row["has_heater"] else None,
        })

    return json.dumps(rooms, indent=2)


# ═══════════════════════════════════════════════════════════════
#  TOOL 2: Set Target Temperature
# ═══════════════════════════════════════════════════════════════

@mcp.tool
def set_target_temperature(room_name: str, target_temp: float) -> str:
    """Set the target temperature for a specific room.

    Args:
        room_name: Name of the room (e.g. "Living Room", "Kitchen")
        target_temp: Desired temperature in Celsius (must be between 10 and 28)
    """
    if target_temp < 10 or target_temp > 28:
        return f"Error: Temperature {target_temp} is outside allowed range (10-28 C)."

    conn = get_db()
    cursor = conn.cursor()

    # Find the room
    cursor.execute("SELECT id, name, target_temp FROM rooms WHERE name LIKE ?",
                   [f"%{room_name}%"])
    room = cursor.fetchone()

    if not room:
        conn.close()
        return f"Error: No room found matching '{room_name}'."

    old_temp = room["target_temp"]
    cursor.execute("UPDATE rooms SET target_temp = ? WHERE id = ?",
                   [target_temp, room["id"]])

    # Log the change
    cursor.execute("""
        INSERT INTO heating_log (room_id, timestamp, action, reason, price_at_time)
        VALUES (?, ?, 'target_changed', ?, NULL)
    """, [room["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          f"Target changed from {old_temp} to {target_temp} C"])

    conn.commit()
    conn.close()
    return f"Target temperature for {room['name']} changed from {old_temp} C to {target_temp} C."


# ═══════════════════════════════════════════════════════════════
#  TOOL 3: Get Current Electricity Price
# ═══════════════════════════════════════════════════════════════

@mcp.tool
def get_current_electricity_price() -> str:
    """Get the current electricity spot price and today's price summary.
    Returns current price in cents/kWh, plus today's average, min, max,
    and cheapest upcoming hours.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Latest price
    cursor.execute("""
        SELECT timestamp, price_cents_kwh
        FROM electricity_prices
        ORDER BY timestamp DESC LIMIT 1
    """)
    current = cursor.fetchone()

    # Today's stats (last 24 entries as proxy)
    cursor.execute("""
        SELECT AVG(price_cents_kwh) AS avg_price,
               MIN(price_cents_kwh) AS min_price,
               MAX(price_cents_kwh) AS max_price
        FROM (SELECT price_cents_kwh FROM electricity_prices ORDER BY timestamp DESC LIMIT 24)
    """)
    stats = cursor.fetchone()

    # Find cheapest upcoming hours
    cursor.execute("""
        SELECT timestamp, price_cents_kwh
        FROM electricity_prices
        WHERE timestamp >= ?
        ORDER BY price_cents_kwh ASC
        LIMIT 3
    """, [current["timestamp"]])
    cheapest = [{"time": row["timestamp"], "price": row["price_cents_kwh"]}
                for row in cursor.fetchall()]

    conn.close()

    result = {
        "current_price_cents_kwh": current["price_cents_kwh"],
        "current_time": current["timestamp"],
        "today_average": round(stats["avg_price"], 2),
        "today_min": stats["min_price"],
        "today_max": stats["max_price"],
        "cheapest_upcoming_hours": cheapest,
    }
    return json.dumps(result, indent=2)


# ═══════════════════════════════════════════════════════════════
#  TOOL 4: Optimize Heating Based on Price
# ═══════════════════════════════════════════════════════════════

@mcp.tool
def optimize_heating(max_price_cents: float = 0) -> str:
    """Optimize heating based on current electricity spot price.

    When the price exceeds the threshold, non-essential room heaters
    are set to eco mode. Essential rooms (Bathroom, Kids Room) are
    never turned off. No room goes below the minimum safe temperature.

    Args:
        max_price_cents: Price threshold in cents/kWh. Pass 0 to use system default.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get threshold from settings if not provided
    if max_price_cents <= 0:
        cursor.execute("SELECT value FROM settings WHERE key = 'max_price_threshold'")
        row = cursor.fetchone()
        max_price_cents = float(row["value"]) if row else 12.0

    # Get minimum allowed temperature
    cursor.execute("SELECT value FROM settings WHERE key = 'min_temp_any_room'")
    row = cursor.fetchone()
    min_temp = float(row["value"]) if row else 15.0

    # Get current price
    cursor.execute("""
        SELECT price_cents_kwh, timestamp
        FROM electricity_prices
        ORDER BY timestamp DESC LIMIT 1
    """)
    price_row = cursor.fetchone()
    current_price = price_row["price_cents_kwh"]

    # Essential rooms that should never be turned off
    essential_rooms = {"Bathroom", "Kids Room"}

    actions = []

    if current_price > max_price_cents:
        # Price is high — reduce heating in non-essential rooms
        cursor.execute("""
            SELECT r.id, r.name, r.current_temp, h.id AS heater_id, h.status
            FROM rooms r
            JOIN heaters h ON r.id = h.room_id
            WHERE h.status != 'off'
        """)

        for room in cursor.fetchall():
            if room["name"] in essential_rooms:
                actions.append(f"  {room['name']}: KEPT ON (essential room)")
                continue

            if room["current_temp"] <= min_temp:
                actions.append(f"  {room['name']}: KEPT ON (at minimum temp {min_temp} C)")
                continue

            # Set to eco
            cursor.execute("UPDATE heaters SET status = 'eco' WHERE id = ?",
                           [room["heater_id"]])
            cursor.execute("""
                INSERT INTO heating_log (room_id, timestamp, action, reason, price_at_time)
                VALUES (?, ?, 'heater_eco', ?, ?)
            """, [room["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  f"Price {current_price} > threshold {max_price_cents} cents/kWh",
                  current_price])

            actions.append(f"  {room['name']}: set to ECO (was {room['status']})")

        conn.commit()
        summary = f"PRICE HIGH ({current_price} cents/kWh > threshold {max_price_cents})"

    else:
        # Price is acceptable — restore heaters
        cursor.execute("""
            SELECT r.id, r.name, h.id AS heater_id, h.status
            FROM rooms r
            JOIN heaters h ON r.id = h.room_id
            WHERE h.status = 'eco' AND h.mode = 'auto'
        """)

        for room in cursor.fetchall():
            cursor.execute("UPDATE heaters SET status = 'on' WHERE id = ?",
                           [room["heater_id"]])
            cursor.execute("""
                INSERT INTO heating_log (room_id, timestamp, action, reason, price_at_time)
                VALUES (?, ?, 'heater_on', ?, ?)
            """, [room["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  f"Price {current_price} <= threshold {max_price_cents} cents/kWh",
                  current_price])

            actions.append(f"  {room['name']}: restored to ON (was eco)")

        conn.commit()
        summary = f"PRICE OK ({current_price} cents/kWh <= threshold {max_price_cents})"

    conn.close()

    if not actions:
        actions.append("  No changes needed.")

    result = f"{summary}\nActions taken:\n" + "\n".join(actions)
    return result


# ═══════════════════════════════════════════════════════════════
#  TOOL 5: Get Heating History
# ═══════════════════════════════════════════════════════════════

@mcp.tool
def get_heating_history(room_name: str = "", limit: int = 20) -> str:
    """Get recent heating system actions from the log.

    Args:
        room_name: Optional filter by room name (partial match OK, empty = all rooms)
        limit: Maximum number of log entries to return (default 20)
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT r.name AS room, l.timestamp, l.action, l.reason, l.price_at_time
        FROM heating_log l
        JOIN rooms r ON l.room_id = r.id
        WHERE 1=1
    """
    params = []

    if room_name:
        query += " AND r.name LIKE ?"
        params.append(f"%{room_name}%")

    query += " ORDER BY l.timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not results:
        return "No heating log entries found."
    return json.dumps(results, indent=2)


# ═══════════════════════════════════════════════════════════════
#  PROMPTS
# ═══════════════════════════════════════════════════════════════

@mcp.prompt
def morning_report() -> str:
    """Generate a morning heating system status report."""
    return """Please generate a morning heating status report:

1. Check all room temperatures (use get_room_temperatures)
2. Get the current electricity price (use get_current_electricity_price)
3. Review overnight heating actions (use get_heating_history)
4. Identify any rooms that are significantly below target
5. Check if current price is favorable for pre-heating
6. Provide recommendations:
   - Should we boost any rooms before the morning price peak?
   - Are there rooms we could reduce to save energy?
   - Expected cost outlook for today based on price forecast"""


@mcp.prompt
def cost_optimization() -> str:
    """Analyze and optimize heating costs."""
    return """Please analyze the heating system for cost optimization:

1. Get current electricity prices and identify cheap/expensive hours
2. Check which heaters are running and their power consumption
3. Calculate approximate hourly heating cost at current price
4. Suggest which rooms could be reduced without comfort impact
5. Recommend optimal heating schedule based on price forecast"""


if __name__ == "__main__":
    mcp.run()
