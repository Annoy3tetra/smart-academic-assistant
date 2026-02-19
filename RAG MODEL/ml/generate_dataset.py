import os
import pandas as pd
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "datasets", "demo_student_dataset.csv")

os.makedirs(os.path.join(BASE_DIR, "datasets"), exist_ok=True)

def assign_performance(cgpa, technical, projects):
    if cgpa > 9 and technical >= 8 and projects >= 3:
        return "Excellent"
    elif cgpa > 8:
        return "Good"
    elif cgpa > 6.5:
        return "Average"
    else:
        return "Poor"

def assign_placement(cgpa, aptitude, backlogs, internships):
    if cgpa > 8 and aptitude > 70 and backlogs == 0:
        return "Placed"
    if internships >= 2 and aptitude > 75:
        return "Placed"
    return "Not_Placed"

def assign_domain(technical, projects):
    if technical >= 8:
        return random.choice(["AI", "Data"])
    elif projects >= 2:
        return "Web"
    else:
        return random.choice(["Web", "Data"])

students = []

for i in range(1, 201):

    attendance = random.randint(50, 100)
    internal = random.randint(45, 95)
    assignment = random.randint(45, 95)
    communication = random.randint(4, 9)
    technical = random.randint(4, 9)
    projects = random.randint(0, 5)
    aptitude = random.randint(50, 95)
    internships = random.randint(0, 3)
    backlogs = random.randint(0, 3)
    cgpa = round(random.uniform(5.5, 9.8), 2)

    domain = assign_domain(technical, projects)
    performance = assign_performance(cgpa, technical, projects)
    placement = assign_placement(cgpa, aptitude, backlogs, internships)

    students.append([
        i,
        attendance,
        internal,
        assignment,
        communication,
        technical,
        projects,
        aptitude,
        internships,
        backlogs,
        cgpa,
        domain,
        performance,
        placement
    ])

columns = [
    "student_id",
    "attendance_percentage",
    "internal_marks",
    "assignment_score",
    "communication_skill",
    "technical_skill",
    "projects_completed",
    "aptitude_score",
    "internships",
    "backlogs",
    "cgpa",
    "preferred_domain",
    "performance_label",
    "placement_label"
]

df = pd.DataFrame(students, columns=columns)

df.to_csv(DATA_PATH, index=False)

print("✅ 200 student dataset generated successfully!")
