def evaluate_placement_readiness(average_score, attendance_percentage, risk_level):

    if risk_level == "HIGH":
        return "NOT READY"

    if average_score >= 75 and attendance_percentage >= 80:
        return "READY"

    if average_score >= 60 and attendance_percentage >= 65:
        return "MODERATE"

    return "NOT READY"
