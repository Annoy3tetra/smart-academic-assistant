import joblib
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "saved_models", "performance_model.pkl")

model = joblib.load(MODEL_PATH)


def predict_performance(average_score, attendance, total_subjects):
    features = np.array([[average_score, attendance, total_subjects]])
    prediction = model.predict(features)[0]
    prediction = max(0, min(100, prediction))
    # Risk classification
    if prediction >= 75:
        risk = "LOW"
    elif prediction >= 60:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    return float(round(prediction, 2)), risk
