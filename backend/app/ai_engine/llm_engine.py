import requests

from app.core.config import OLLAMA_MODEL, OLLAMA_URL


def generate_with_phi3(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as err:
        return f"Ollama request failed: {err}"
    except ValueError:
        return "Ollama returned an invalid JSON response."

    answer = str(data.get("response", "")).strip()
    return answer or "Ollama returned an empty response."
