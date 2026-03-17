# school_mcp_server.py
# MCP Day 6 - Demo 2: School Student Records MCP Server
# Exposes a SQLite school database to any MCP client
#
# Setup:     python create_school_db.py    (creates school.db)
# Inspector: fastmcp dev school_mcp_server.py
# Stdio:     python school_mcp_server.py
#
# Claude Code config (~/.claude/mcp.json):
# {
#   "mcpServers": {
#     "school-records": {
#       "command": "python",
#       "args": ["/full/path/to/school_mcp_server.py"]
#     }
#   }
# }

import sqlite3
import json
from fastmcp import FastMCP

mcp = FastMCP("School Records")
DB_PATH = "school.db"


def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════════════
#  RESOURCES — Read-only data the LLM can access for context
# ═══════════════════════════════════════════════════════════════

@mcp.resource("schema://database/tables")
def get_schema() -> str:
    """Database schema showing all tables and their columns.
    Use this to understand the data structure before writing queries.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    schemas = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return "\n\n".join(schemas)


@mcp.resource("data://students/all")
def get_all_students() -> str:
    """Complete list of all enrolled students with their details."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, enrollment_year, program FROM students ORDER BY name"
    )
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return json.dumps(students, indent=2)


@mcp.resource("data://courses/all")
def get_all_courses() -> str:
    """List of all courses offered."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, code, credits, teacher, semester FROM courses ORDER BY semester DESC, name"
    )
    courses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return json.dumps(courses, indent=2)


# ═══════════════════════════════════════════════════════════════
#  TOOLS — Functions the LLM can call to query and act on data
# ═══════════════════════════════════════════════════════════════

@mcp.tool
def query_grades(
    student_name: str = "",
    course_name: str = "",
    semester: str = "",
    min_grade: int = 0
) -> str:
    """Query student grades with optional filters.

    All parameters are optional. Omit or leave empty to skip a filter.
    Grade scale: 1-5 (Finnish system, 5 = excellent).

    Args:
        student_name: Filter by student name (partial match OK)
        course_name: Filter by course name (partial match OK)
        semester: Filter by semester, e.g. "Spring 2025" or "Fall 2024"
        min_grade: Only show grades >= this value (1-5)
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT s.name AS student,
               c.name AS course,
               c.semester,
               g.grade,
               g.points,
               g.feedback
        FROM grades g
        JOIN students s ON g.student_id = s.id
        JOIN courses c ON g.course_id = c.id
        WHERE 1=1
    """
    params = []

    if student_name:
        query += " AND s.name LIKE ?"
        params.append(f"%{student_name}%")
    if course_name:
        query += " AND c.name LIKE ?"
        params.append(f"%{course_name}%")
    if semester:
        query += " AND c.semester LIKE ?"
        params.append(f"%{semester}%")
    if min_grade > 0:
        query += " AND g.grade >= ?"
        params.append(min_grade)

    query += " ORDER BY c.semester DESC, c.name, s.name"

    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not results:
        return "No matching grade records found."
    return json.dumps(results, indent=2)


@mcp.tool
def calculate_course_statistics(course_name: str, semester: str = "") -> str:
    """Calculate grade statistics for a course.

    Returns: student count, average grade, grade distribution,
    pass rate, and top/struggling students.

    Args:
        course_name: Course name (partial match OK)
        semester: Optional semester filter, e.g. "Spring 2025"
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT s.name AS student, g.grade, g.points, c.name AS course, c.semester
        FROM grades g
        JOIN students s ON g.student_id = s.id
        JOIN courses c ON g.course_id = c.id
        WHERE c.name LIKE ?
    """
    params = [f"%{course_name}%"]

    if semester:
        query += " AND c.semester LIKE ?"
        params.append(f"%{semester}%")

    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not results:
        return f"No grades found for course matching '{course_name}'"

    grades = [r["grade"] for r in results]
    points = [r["points"] for r in results]

    top_students = [r["student"] for r in results if r["grade"] >= 5]
    struggling = [r["student"] for r in results if r["grade"] <= 2]

    stats = {
        "course": results[0]["course"],
        "semester": results[0]["semester"],
        "total_students": len(grades),
        "average_grade": round(sum(grades) / len(grades), 2),
        "average_points": round(sum(points) / len(points), 1),
        "pass_rate": f"{sum(1 for g in grades if g >= 1) / len(grades) * 100:.0f}%",
        "grade_distribution": {
            str(g): grades.count(g) for g in sorted(set(grades))
        },
        "top_students_grade_5": top_students if top_students else "None",
        "students_needing_support_grade_2_or_below": struggling if struggling else "None",
    }
    return json.dumps(stats, indent=2)


@mcp.tool
def get_attendance_report(
    course_name: str = "AI Application Development",
    student_name: str = ""
) -> str:
    """Get attendance summary for a course, optionally filtered by student.

    Returns attendance rate and detailed day-by-day breakdown.

    Args:
        course_name: Course name (partial match OK)
        student_name: Optional student name filter (partial match OK)
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT s.name AS student, a.date, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN courses c ON a.course_id = c.id
        WHERE c.name LIKE ?
    """
    params = [f"%{course_name}%"]

    if student_name:
        query += " AND s.name LIKE ?"
        params.append(f"%{student_name}%")

    query += " ORDER BY s.name, a.date"

    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not rows:
        return "No attendance records found."

    # Group by student
    from collections import defaultdict
    by_student = defaultdict(list)
    for row in rows:
        by_student[row["student"]].append(row)

    report = []
    for student, records in by_student.items():
        total = len(records)
        present = sum(1 for r in records if r["status"] == "present")
        late = sum(1 for r in records if r["status"] == "late")
        absent = sum(1 for r in records if r["status"] == "absent")
        rate = (present + late) / total * 100

        report.append({
            "student": student,
            "total_days": total,
            "present": present,
            "late": late,
            "absent": absent,
            "attendance_rate": f"{rate:.0f}%",
        })

    return json.dumps(report, indent=2)


@mcp.tool
def find_students_needing_support(semester: str = "Spring 2025") -> str:
    """Identify students who may need academic support.

    Finds students with grade 2 or below in any course,
    or attendance rate below 80%.

    Args:
        semester: Which semester to check (default: Spring 2025)
    """
    conn = get_db()
    cursor = conn.cursor()

    # Low grades
    cursor.execute("""
        SELECT s.name AS student, c.name AS course, g.grade, g.feedback
        FROM grades g
        JOIN students s ON g.student_id = s.id
        JOIN courses c ON g.course_id = c.id
        WHERE g.grade <= 2 AND c.semester LIKE ?
        ORDER BY g.grade, s.name
    """, [f"%{semester}%"])

    low_grades = [dict(row) for row in cursor.fetchall()]

    # Low attendance
    cursor.execute("""
        SELECT s.name AS student,
               COUNT(*) AS total_days,
               SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS absences
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN courses c ON a.course_id = c.id
        WHERE c.semester LIKE ?
        GROUP BY s.name
        HAVING (1.0 * SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) / COUNT(*)) > 0.2
    """, [f"%{semester}%"])

    low_attendance = [dict(row) for row in cursor.fetchall()]
    conn.close()

    result = {
        "semester": semester,
        "students_with_low_grades": low_grades if low_grades else "None found",
        "students_with_low_attendance": low_attendance if low_attendance else "None found",
    }
    return json.dumps(result, indent=2)


@mcp.tool
def compare_students(student_names: str) -> str:
    """Compare academic performance of two or more students side by side.

    Args:
        student_names: Comma-separated student names, e.g. "Emma, Mikko"
    """
    names = [n.strip() for n in student_names.split(",")]

    conn = get_db()
    cursor = conn.cursor()

    comparisons = []
    for name in names:
        cursor.execute("""
            SELECT s.name AS student,
                   c.name AS course,
                   c.semester,
                   g.grade,
                   g.points
            FROM grades g
            JOIN students s ON g.student_id = s.id
            JOIN courses c ON g.course_id = c.id
            WHERE s.name LIKE ?
            ORDER BY c.semester DESC, c.name
        """, [f"%{name}%"])

        rows = [dict(row) for row in cursor.fetchall()]
        if rows:
            grades = [r["grade"] for r in rows]
            comparisons.append({
                "student": rows[0]["student"],
                "courses_taken": len(rows),
                "average_grade": round(sum(grades) / len(grades), 2),
                "highest_grade": max(grades),
                "lowest_grade": min(grades),
                "details": rows,
            })
        else:
            comparisons.append({"student": name, "error": "Not found"})

    conn.close()
    return json.dumps(comparisons, indent=2)


# ═══════════════════════════════════════════════════════════════
#  PROMPTS — Reusable templates for common interactions
# ═══════════════════════════════════════════════════════════════

@mcp.prompt
def semester_report(semester: str = "Spring 2025") -> str:
    """Generate a comprehensive semester report with analysis."""
    return f"""Please generate a comprehensive report for {semester}:

1. First, list all courses offered in {semester}
2. Calculate statistics for each course (use calculate_course_statistics)
3. Identify top-performing students (grade 5) across all courses
4. Identify students who may need academic support (use find_students_needing_support)
5. Check attendance patterns if data is available
6. Provide a summary with:
   - Overall semester performance trends
   - Recommendations for course improvements
   - Specific student interventions needed"""


@mcp.prompt
def student_profile(student_name: str) -> str:
    """Create a complete academic profile for a student."""
    return f"""Please create a complete academic profile for {student_name}:

1. Look up all their grades across all semesters
2. Check their attendance records
3. Compare their performance with class averages
4. Highlight strengths and areas for improvement
5. Provide actionable recommendations"""


if __name__ == "__main__":
    mcp.run()
