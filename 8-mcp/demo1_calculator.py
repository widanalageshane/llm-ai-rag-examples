# demo1_calculator.py
# MCP Day 6 - Demo 1: Minimal MCP Server (No Database)
# Purpose: Show the bare mechanics of MCP — decorated Python functions become tools
#
# Run with MCP Inspector:   fastmcp dev demo1_calculator.py
# Run as stdio server:      python demo1_calculator.py

from fastmcp import FastMCP

mcp = FastMCP("Calculator Demo")


# --- Tools (LLM-callable functions) ---

@mcp.tool
def add(a: float, b: float) -> float:
    """Add two numbers together and return the result."""
    return a + b


@mcp.tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together and return the result."""
    return a * b


@mcp.tool
def convert_celsius_to_fahrenheit(celsius: float) -> float:
    """Convert a temperature from Celsius to Fahrenheit."""
    return (celsius * 9 / 5) + 32


@mcp.tool
def calculate_bmi(weight_kg: float, height_cm: float) -> str:
    """Calculate Body Mass Index (BMI) from weight in kg and height in cm.
    Returns the BMI value and a category label.
    """
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal weight"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    return f"BMI: {bmi:.1f} ({category})"


# --- Resources (read-only data the LLM can access) ---

@mcp.resource("config://version")
def get_version() -> str:
    """Current server version."""
    return "1.0.0"


@mcp.resource("config://capabilities")
def get_capabilities() -> str:
    """Description of what this server can do."""
    return (
        "This is a demo calculator MCP server. "
        "It can add, multiply, convert temperatures, and calculate BMI. "
        "It demonstrates the basic MCP server pattern: "
        "Python functions decorated with @mcp.tool become callable by any MCP client."
    )


# --- Prompts (reusable interaction templates) ---

@mcp.prompt
def unit_conversion_helper() -> str:
    """Help the user convert between different units."""
    return (
        "The user wants to convert between units. "
        "Use the available conversion tools. "
        "If a conversion tool isn't available, calculate it manually and show your work."
    )


if __name__ == "__main__":
    mcp.run()
