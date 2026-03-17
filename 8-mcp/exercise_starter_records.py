# exercise_starter_records.py
# MCP Day 6 - Exercise Option B: Extended Student Records MCP Server
# ═══════════════════════════════════════════════════════════════
#
# YOUR TASK: Build on the demo school_mcp_server.py by adding tools
# for attendance tracking and assignment management.
#
# The database (school.db from create_school_db.py) already has
# 'attendance' and 'grades' tables. You need to add tools that
# let an LLM work with this data.
#
# SETUP:
#   pip install fastmcp
#   python create_school_db.py     (creates school.db with attendance data)
#   fastmcp dev exercise_starter_records.py   (test with Inspector)
#
# WHAT TO IMPLEMENT:
#   1. record_attendance      (Tool)  — mark a student present/absent/late
#   2. get_attendance_report  (Tool)  — attendance summary for a course
#   3. get_student_summary    (Tool)  — full overview for one student
#   4. find_at_risk_students  (Tool)  — students with low grades + poor attendance
#   5. At least one Resource and one Prompt
#
# HINTS:
#   - The 'attendance' table has: student_id, course_id, date, status
#   - Status values: 'present', 'absent', 'late'
#   - Use JOIN queries to connect students, courses, grades, and attendance
#   - Return JSON strings from all tools
#   - Write clear docstrings — the LLM reads them!
# ═══════════════════════════════════════════════════════════════

import sqlite3
import json
from fastmcp import FastMCP

mcp = FastMCP("Student Records Extended")
DB_PATH = "school.db"


def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════════════
#  RESOURCES
# ═══════════════════════════════════════════════════════════════

@mcp.resource("schema://database/tables")
def get_schema() -> str:
    """Database schema showing all tables and their columns."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    schemas = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return "\n\n".join(schemas)


# TODO: Add a resource that returns a list of all students with basic info
# @mcp.resource("data://students/all")
# def get_all_students() -> str:
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 1: Record Attendance
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# Insert a new attendance record for a student in a course
# Validate: status must be 'present', 'absent', or 'late'
# Look up student and course by name (partial match OK)
#
# @mcp.tool
# def record_attendance(student_name: str, course_name: str,
#                       date: str, status: str) -> str:
#     """Record attendance for a student in a course.
#
#     Args:
#         student_name: Student's name (partial match OK)
#         course_name: Course name (partial match OK)
#         date: Date in YYYY-MM-DD format
#         status: One of 'present', 'absent', or 'late'
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 2: Get Attendance Report
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# Show attendance summary per student for a given course
# Include: total days, present count, late count, absent count, rate
#
# @mcp.tool
# def get_attendance_report(course_name: str) -> str:
#     """Get attendance summary for all students in a course.
#
#     Args:
#         course_name: Course name (partial match OK)
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 3: Get Student Summary
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# Create a complete overview of one student:
# - Personal info (name, email, program, enrollment year)
# - All grades across all courses
# - Attendance statistics
# - Overall GPA (average grade)
#
# @mcp.tool
# def get_student_summary(student_name: str) -> str:
#     """Get a complete academic profile for a student.
#     Includes grades, attendance, and overall statistics.
#
#     Args:
#         student_name: Student's name (partial match OK)
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  TOOL 4: Find At-Risk Students
# ═══════════════════════════════════════════════════════════════

# TODO: Implement this tool
# Find students who might need support based on:
# - Grade 2 or below in any course
# - Attendance rate below 80%
# - Combine both signals for a "risk score"
#
# @mcp.tool
# def find_at_risk_students() -> str:
#     """Identify students who may need academic support.
#     Checks for low grades and poor attendance across all courses.
#     """
#     ...


# ═══════════════════════════════════════════════════════════════
#  PROMPTS
# ═══════════════════════════════════════════════════════════════

# TODO: Add at least one prompt template
# Idea: A "class review" prompt that analyzes one specific course
#
# @mcp.prompt
# def class_review(course_name: str = "AI Application Development") -> str:
#     """Generate a comprehensive review of a course."""
#     return f"""..."""


if __name__ == "__main__":
    mcp.run()
