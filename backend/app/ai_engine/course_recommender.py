import json
import os
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


def _normalize_provider(provider: str) -> str:
    p = provider.strip().lower()
    if p in {"coursera", "youtube", "nptel", "edx", "udemy"}:
        return p.title() if p != "edx" else "edX"
    return "YouTube"


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


def _fallback_recommendations(subjects: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    weakest = sorted(subjects, key=lambda item: float(item["score"]))[:top_n]
    recommendations = []

    for item in weakest:
        subject = str(item["name"]).strip()
        score = float(item["score"])
        recommendations.append(
            {
                "title": f"{subject} Mastery Bootcamp",
                "focus_subject": subject,
                "provider": "YouTube",
                "course_url": _build_course_url("YouTube", "Mastery Bootcamp", subject),
                "reason": f"Your score in {subject} is {score:.1f}. This course targets core gaps and practice.",
                "level": _level_from_score(score),
                "priority": _priority_from_score(score),
                "estimated_hours": 20 if score < 50 else 14 if score < 70 else 10,
            }
        )

    return {
        "model_used": "heuristic-fallback",
        "weak_subjects": _weak_subjects(subjects),
        "recommendations": recommendations,
    }


def _extract_json_block(raw_text: str) -> dict[str, Any] | None:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None


def _normalize_output(candidate: dict[str, Any], subjects: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    weak_subjects = candidate.get("weak_subjects")
    if not isinstance(weak_subjects, list) or not weak_subjects:
        weak_subjects = _weak_subjects(subjects)
    weak_subjects = [str(item) for item in weak_subjects][:3]

    recs = candidate.get("recommendations")
    if not isinstance(recs, list) or not recs:
        return _fallback_recommendations(subjects, top_n)

    normalized = []
    for rec in recs[:top_n]:
        if not isinstance(rec, dict):
            continue

        title = str(rec.get("title", "")).strip()
        focus_subject = str(rec.get("focus_subject", "")).strip()
        reason = str(rec.get("reason", "")).strip()
        provider = _normalize_provider(str(rec.get("provider", "YouTube")))
        course_url = str(rec.get("course_url", "")).strip()
        level = str(rec.get("level", "Intermediate")).strip().title()
        priority = str(rec.get("priority", "Medium")).strip().title()
        estimated = rec.get("estimated_hours", 12)

        if not title or not focus_subject or not reason:
            continue
        if not course_url:
            course_url = _build_course_url(provider, title, focus_subject)
        if level not in {"Beginner", "Intermediate", "Advanced"}:
            level = "Intermediate"
        if priority not in {"High", "Medium", "Low"}:
            priority = "Medium"
        try:
            estimated = int(estimated)
        except (TypeError, ValueError):
            estimated = 12
        estimated = max(1, min(300, estimated))

        normalized.append(
            {
                "title": title,
                "focus_subject": focus_subject,
                "provider": provider,
                "course_url": course_url,
                "reason": reason,
                "level": level,
                "priority": priority,
                "estimated_hours": estimated,
            }
        )

    if not normalized:
        return _fallback_recommendations(subjects, top_n)

    return {
        "model_used": "gemini",
        "weak_subjects": weak_subjects,
        "recommendations": normalized,
    }


def recommend_courses_with_gemini(
    subjects: list[dict[str, Any]], attendance: float | None, top_n: int
) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _fallback_recommendations(subjects, top_n)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
You are an academic recommendation engine.
Given subject-wise marks and attendance, return ONLY valid JSON with this shape:
{{
  "weak_subjects": ["subject1", "subject2", "subject3"],
  "recommendations": [
    {{
      "title": "string",
      "focus_subject": "string",
      "provider": "Coursera|YouTube|NPTEL|edX|Udemy",
      "course_url": "https://...",
      "reason": "string (max 28 words)",
      "level": "Beginner|Intermediate|Advanced",
      "priority": "High|Medium|Low",
      "estimated_hours": 1-300 integer
    }}
  ]
}}

Rules:
- recommendations count must be exactly {top_n}
- focus on weakest subjects first
- practical, skill-building courses, not generic motivation
- include valid public course/search URL for each recommendation
- no markdown, no explanation, JSON only

Input data:
subjects={json.dumps(subjects, ensure_ascii=True)}
attendance={attendance}
"""

        response = model.generate_content(prompt)
        raw_text = (response.text or "").strip()
        parsed = _extract_json_block(raw_text)
        if not parsed:
            return _fallback_recommendations(subjects, top_n)
        return _normalize_output(parsed, subjects, top_n)
    except Exception:
        return _fallback_recommendations(subjects, top_n)
