from typing import Any
from urllib.parse import quote_plus


def _weak_subjects(subjects: list[dict[str, Any]], limit: int = 3) -> list[str]:
    sorted_subjects = sorted(subjects, key=lambda item: float(item["score"]))
    return [str(item["name"]) for item in sorted_subjects[:limit]]


def _priority_from_score(score: float) -> str:
    if score < 50:
        return "High"
    if score < 70:
        return "Medium"
    return "Low"


def _level_from_score(score: float) -> str:
    if score < 50:
        return "Beginner"
    if score < 75:
        return "Intermediate"
    return "Advanced"


def _build_course_url(provider: str, title: str, subject: str) -> str:
    query = quote_plus(f"{title} {subject} course")
    if provider == "Coursera":
        return f"https://www.coursera.org/search?query={query}"
    if provider == "Nptel":
        return f"https://onlinecourses.nptel.ac.in/noc25_cs/search?query={query}"
    if provider == "edX":
        return f"https://www.edx.org/search?q={query}"
    if provider == "Udemy":
        return f"https://www.udemy.com/courses/search/?q={query}"
    return f"https://www.youtube.com/results?search_query={query}"


def _fallback_recommendations(
    subjects: list[dict[str, Any]],
    attendance: float | None,
    top_n: int,
) -> dict[str, Any]:
    weakest = sorted(subjects, key=lambda item: float(item["score"]))[:top_n]
    recommendations = []
    attendance_note = ""
    if attendance is not None and attendance < 75:
        attendance_note = " Pair this with a weekly attendance improvement plan."

    for item in weakest:
        subject = str(item["name"]).strip()
        score = float(item["score"])
        recommendations.append(
            {
                "title": f"{subject} Mastery Bootcamp",
                "focus_subject": subject,
                "provider": "YouTube",
                "course_url": _build_course_url("YouTube", "Mastery Bootcamp", subject),
                "reason": (
                    f"Your score in {subject} is {score:.1f}. "
                    f"This course targets core gaps and practice.{attendance_note}"
                ),
                "level": _level_from_score(score),
                "priority": _priority_from_score(score),
                "estimated_hours": 20 if score < 50 else 14 if score < 70 else 10,
            }
        )

    return {
        "model_used": "local-heuristic",
        "weak_subjects": _weak_subjects(subjects),
        "recommendations": recommendations,
    }


def recommend_courses(
    subjects: list[dict[str, Any]], attendance: float | None, top_n: int
) -> dict[str, Any]:
    return _fallback_recommendations(subjects, attendance, top_n)
