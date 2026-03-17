# exercise_starter_heating.py
# MCP Day 6 - Exercise Option A: House Heating System MCP Server
# ═══════════════════════════════════════════════════════════════
#
# YOUR TASK: Complete the TODO sections to build an MCP server that lets
# an LLM monitor and control a house heating system with electricity
# spot price awareness.
#
# SETUP:
#   pip install fastmcp
#   python create_heating_db.py     (creates heating.db)
#   fastmcp dev exercise_starter_heating.py   (test with Inspector)
#
# WHAT TO IMPLEMENT:
#   1. get_room_temperatures   (Tool)  — query current temps for all rooms
#   2. set_target_temperature  (Tool)  — change a room's target temperature
#   3. get_current_price       (Tool)  — get the latest electricity spot price
#   4. optimize_heating        (Tool)  — turn off/eco heaters when price is high
#   5. get_heating_history     (Tool)  — view recent heating actions
#   6. At least one Resource and one Prompt
#
# HINTS:
#   - Use get_db() to get a database connection
#   - conn.row_factory = sqlite3.Row gives dict-like access: row["column_name"]
#   - Return JSON strings from tools (the LLM reads text, not Python objects)
#   - Docstrings are important — the LLM reads them to understand what tools do
#   - Type hints matter — FastMCP uses them to generate parameter schemas
#
# BONUS CHALLENGES:
#   - Add a tool that calculates estimated heating cost for the next 24 hours
#   - Add a tool that recommends the cheapest hours to run the heaters
#   - Add a resource that returns a "system health" summary
# ═══════════════════════════════════════════════════════════════

import sqlite3
import json
from fastmcp import FastMCP

mcp = FastMCP("House Heating System")
DB_PATH = "heating.db"


def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════════════
#  RESOURCES — Read-only context data
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


# TODO: Add a resource that returns system settings
# Hint: Query the 'settings' table and return all key-value pairs
#
# @mcp.resource("config://heating/settings")
# def get_settings() -> str:
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 1: Get Room Temperatures
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# Query the 'rooms' table to show current and target temperatures
# Include: room name, floor, current_temp, target_temp, and whether temp
# is above or below target
#
# @mcp.tool
# def get_room_temperatures() -> str:
#     """Get current temperatures for all rooms in the house.
#     Shows each room's current temp, target temp, and status.
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 2: Set Target Temperature
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# Update the target_temp for a specific room
# Validate: temperature should be between 10 and 28 degrees
# Return a confirmation message
#
# @mcp.tool
# def set_target_temperature(room_name: str, target_temp: float) -> str:
#     """Set the target temperature for a room.
#
#     Args:
#         room_name: Name of the room (e.g., "Living Room", "Kitchen")
#         target_temp: Desired temperature in Celsius (10-28 range)
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 3: Get Current Electricity Price
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# Query the electricity_prices table for the most recent price
# Also show the average price for today and the min/max range
#
# @mcp.tool
# def get_current_electricity_price() -> str:
#     """Get the current electricity spot price and today's price summary.
#     Returns current price in cents/kWh, plus today's average, min, and max.
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 4: Optimize Heating Based on Price
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# This is the most interesting tool — it makes decisions!
# If current price exceeds max_price_cents:
#   - Set heaters in non-essential rooms to 'eco' or 'off'
#   - Never reduce below min_temp_any_room (from settings)
#   - Log the action to heating_log
# If price is low, turn heaters back on
#
# @mcp.tool
# def optimize_heating(max_price_cents: float = 0) -> str:
#     """Optimize heating based on electricity price.
#     Turns heaters to eco/off in non-essential rooms when price is high.
#     If max_price_cents is 0, uses the threshold from system settings.
#
#     Args:
#         max_price_cents: Price threshold in cents/kWh (0 = use system default)
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 5: Get Heating History
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# Query the heating_log table for recent actions
# Optionally filter by room name
# Show: room, timestamp, action, reason, price at time
#
# @mcp.tool
# def get_heating_history(room_name: str = "", limit: int = 20) -> str:
#     """Get recent heating system actions from the log.
#
#     Args:
#         room_name: Optional filter by room name (partial match OK)
#         limit: Maximum number of entries to return (default 20)
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  PROMPTS — Reusable interaction templates
# ═══════════════════════════════════════════════════════════════

# TODO: Add at least one prompt template
# Idea: A "morning report" prompt that checks all room temperatures,
# current price, and recent heating activity
#
# @mcp.prompt
# def morning_report() -> str:
#     """Generate a morning heating system status report."""
#     return """..."""


if __name__ == "__main__":
    mcp.run()
