import joblib
import os
import numpy as np
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "saved_models", "performance_model.pkl")


@lru_cache(maxsize=1)
def _get_model():
    return joblib.load(MODEL_PATH)


def predict_performance(average_score, attendance, total_subjects):
    features = np.array([[average_score, attendance, total_subjects]])
    prediction = _get_model().predict(features)[0]
    prediction = max(0, min(100, prediction))
    # Risk classification
    if prediction >= 80:
        risk = "LOW"
    elif prediction <80 and prediction >= 60:
        risk = "BALANCED"
    elif prediction <60 and prediction >= 40:
        risk = "MEDIUM"
    elif prediction <40 and prediction >= 20:
        risk = "HIGH"
    else:
        risk = "VERY HIGH"

    return float(round(prediction, 2)), risk
