# create_school_db.py
# MCP Day 6 - Demo 2: Create the School Student Records database
# Run this BEFORE starting the MCP server
#
# Usage: python create_school_db.py
# Output: school.db (SQLite database)

import sqlite3
import os

DB_PATH = "school.db"

# Remove old database if it exists
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"Removed existing {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Create Tables ──────────────────────────────────────────────

cursor.execute('''
CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    enrollment_year INTEGER,
    program TEXT
)''')

cursor.execute('''
CREATE TABLE courses (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    credits INTEGER,
    teacher TEXT,
    semester TEXT
)''')

cursor.execute('''
CREATE TABLE grades (
    id INTEGER PRIMARY KEY,
    student_id INTEGER REFERENCES students(id),
    course_id INTEGER REFERENCES courses(id),
    grade INTEGER,
    points REAL,
    feedback TEXT
)''')

cursor.execute('''
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY,
    student_id INTEGER REFERENCES students(id),
    course_id INTEGER REFERENCES courses(id),
    date TEXT,
    status TEXT CHECK(status IN ('present', 'absent', 'late'))
)''')

# ── Insert Sample Data ─────────────────────────────────────────

students = [
    (1,  "Emma Virtanen",       "emma.v@school.fi",    2023, "ICT"),
    (2,  "Mikko Korhonen",      "mikko.k@school.fi",   2023, "ICT"),
    (3,  "Sara Nieminen",       "sara.n@school.fi",    2022, "ICT"),
    (4,  "Antti Makela",        "antti.m@school.fi",   2023, "ICT"),
    (5,  "Laura Hamalainen",    "laura.h@school.fi",   2022, "ICT"),
    (6,  "Juha Lehtonen",       "juha.l@school.fi",    2023, "ICT"),
    (7,  "Minna Saarinen",      "minna.s@school.fi",   2022, "ICT"),
    (8,  "Timo Laine",          "timo.l@school.fi",    2023, "Software Engineering"),
    (9,  "Kaisa Jarvinen",      "kaisa.j@school.fi",   2023, "Software Engineering"),
    (10, "Pekka Heikkinen",     "pekka.h@school.fi",   2022, "Software Engineering"),
]

courses = [
    (1, "AI Application Development",  "ICT301", 5, "Prof. Laine",    "Spring 2025"),
    (2, "Database Systems",             "ICT202", 5, "Prof. Koskinen", "Spring 2025"),
    (3, "Web Development",              "ICT203", 5, "Prof. Jarvinen", "Spring 2025"),
    (4, "AI Application Development",  "ICT301", 5, "Prof. Laine",    "Fall 2024"),
    (5, "Database Systems",             "ICT202", 5, "Prof. Koskinen", "Fall 2024"),
]

# Grade scale: 1-5 (Finnish system, 5 = excellent, 0 = fail)
grades_data = [
    # Spring 2025 - AI Application Development (course 1)
    (1,  1, 1, 5, 95.0, "Excellent project work and exam performance"),
    (2,  2, 1, 3, 71.0, "Solid understanding, needs more practice with RAG"),
    (3,  4, 1, 2, 58.0, "Struggles with implementation, good theoretical grasp"),
    (4,  6, 1, 4, 84.0, "Very good, strong coding skills"),
    (5,  8, 1, 5, 92.0, "Outstanding work throughout the course"),
    (6,  9, 1, 4, 81.0, "Good performance, creative project idea"),
    # Spring 2025 - Database Systems (course 2)
    (7,  1, 2, 4, 82.0, "Good SQL skills, could improve normalization"),
    (8,  2, 2, 4, 80.0, "Consistent performer"),
    (9,  4, 2, 3, 68.0, "Average performance, attend office hours"),
    (10, 6, 2, 5, 93.0, "Best SQL project in the class"),
    # Spring 2025 - Web Development (course 3)
    (11, 2, 3, 5, 93.0, "Exceptional frontend skills"),
    (12, 4, 3, 3, 70.0, "Functional project, needs better CSS"),
    (13, 8, 3, 4, 85.0, "Clean code, good use of React"),
    (14, 9, 3, 3, 72.0, "Completed all requirements"),
    # Fall 2024 - AI Application Development (course 4)
    (15, 3, 4, 4, 85.0, "Strong understanding of embeddings"),
    (16, 5, 4, 5, 96.0, "Top student, excellent project"),
    (17, 7, 4, 3, 74.0, "Good effort, needs more practice"),
    (18, 10, 4, 4, 83.0, "Solid work throughout"),
    # Fall 2024 - Database Systems (course 5)
    (19, 3, 5, 5, 91.0, "Outstanding SQL and NoSQL knowledge"),
    (20, 5, 5, 4, 87.0, "Very good, creative database design"),
    (21, 7, 5, 2, 55.0, "Barely passed, needs significant improvement"),
    (22, 10, 5, 5, 94.0, "Excellent in all areas"),
]

# Attendance for Spring 2025 AI course (course 1)
attendance_data = []
att_id = 1
days = ["2025-01-13", "2025-01-14", "2025-01-15", "2025-01-16", "2025-01-17",
        "2025-01-20", "2025-01-21", "2025-01-22", "2025-01-23", "2025-01-24"]
spring_ai_students = [1, 2, 4, 6, 8, 9]

import random
random.seed(42)  # Reproducible

for student_id in spring_ai_students:
    for day in days:
        # Most students attend most days
        r = random.random()
        if r < 0.80:
            status = "present"
        elif r < 0.92:
            status = "late"
        else:
            status = "absent"
        attendance_data.append((att_id, student_id, 1, day, status))
        att_id += 1

cursor.executemany("INSERT INTO students VALUES (?,?,?,?,?)", students)
cursor.executemany("INSERT INTO courses VALUES (?,?,?,?,?,?)", courses)
cursor.executemany("INSERT INTO grades VALUES (?,?,?,?,?,?)", grades_data)
cursor.executemany("INSERT INTO attendance VALUES (?,?,?,?,?)", attendance_data)

conn.commit()
conn.close()

print(f"Database created: {DB_PATH}")
print(f"  {len(students)} students")
print(f"  {len(courses)} courses")
print(f"  {len(grades_data)} grade records")
print(f"  {len(attendance_data)} attendance records")
print()
print("Tables: students, courses, grades, attendance")
print("Ready to use with school_mcp_server.py")
