import os
import pickle
import pandas as pd

# ==============================
# 1. Load Models and Encoders
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")

with open(os.path.join(MODEL_DIR, "performance.pkl"), "rb") as f:
    performance_model = pickle.load(f)

with open(os.path.join(MODEL_DIR, "placement.pkl"), "rb") as f:
    placement_model = pickle.load(f)

with open(os.path.join(MODEL_DIR, "recommendation.pkl"), "rb") as f:
    recommendation_model = pickle.load(f)

with open(os.path.join(MODEL_DIR, "label_encoders.pkl"), "rb") as f:
    label_encoders = pickle.load(f)

# ==============================
# 2. Create New Student Input
# ==============================

new_student = {
    "attendance_percentage": 85,
    "internal_marks": 80,
    "assignment_score": 82,
    "communication_skill": 7,
    "technical_skill": 8,
    "projects_completed": 3,
    "aptitude_score": 75,
    "internships": 1,
    "backlogs": 0,
    "cgpa": 8.3,
    "preferred_domain": "AI"
}

# Convert to DataFrame
input_df = pd.DataFrame([new_student])

# Encode preferred_domain
le_domain = label_encoders["preferred_domain"]
input_df["preferred_domain"] = le_domain.transform(input_df["preferred_domain"])

# ==============================
# 3. Make Predictions
# ==============================

performance_pred = performance_model.predict(input_df)
placement_pred = placement_model.predict(input_df)
recommendation_pred = recommendation_model.predict(input_df)

# Decode predictions
le_performance = label_encoders["performance_label"]
le_placement = label_encoders["placement_label"]
le_domain = label_encoders["preferred_domain"]

performance_result = le_performance.inverse_transform(performance_pred)
placement_result = le_placement.inverse_transform(placement_pred)
recommendation_result = le_domain.inverse_transform(recommendation_pred)

# ==============================
# 4. Print Results
# ==============================

print("🎯 Predicted Performance:", performance_result[0])
print("💼 Placement Status:", placement_result[0])
print("📚 Recommended Domain:", recommendation_result[0])

# ==============================
# 5. Suggestion Engine
# ==============================

def generate_suggestions(student, performance, placement):
    suggestions = []

    if student["technical_skill"] < 6:
        suggestions.append("Improve technical skills by practicing DSA and projects.")

    if student["communication_skill"] < 6:
        suggestions.append("Work on communication skills through mock interviews and presentations.")

    if student["projects_completed"] < 2:
        suggestions.append("Build more real-world projects to strengthen your resume.")

    if student["aptitude_score"] < 65:
        suggestions.append("Practice aptitude questions daily for placement preparation.")

    if student["backlogs"] > 0:
        suggestions.append("Clear backlogs as soon as possible to improve placement chances.")

    if placement == "Not_Placed":
        suggestions.append("Focus on internships and resume building.")

    if performance == "Poor":
        suggestions.append("Improve study consistency and attendance.")

    if not suggestions:
        suggestions.append("Keep up the great work! Maintain consistency.")

    return suggestions


suggestions = generate_suggestions(new_student,
                                   performance_result[0],
                                   placement_result[0])

print("\n📌 Personalized Suggestions:")
for s in suggestions:
    print("-", s)
