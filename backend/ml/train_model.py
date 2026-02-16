import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import joblib
import os

# Generate synthetic training data
np.random.seed(42)

n = 200

average_score = np.random.uniform(40, 95, n)
attendance = np.random.uniform(50, 100, n)
total_subjects = np.random.randint(4, 8, n)

# Simple synthetic formula
final_score = (
    0.6 * average_score +
    0.3 * attendance +
    0.1 * total_subjects +
    np.random.normal(0, 3, n)
)

X = np.column_stack((average_score, attendance, total_subjects))
y = final_score

model = LinearRegression()
model.fit(X, y)

# Save model
os.makedirs("saved_models", exist_ok=True)
joblib.dump(model, "saved_models/performance_model.pkl")

print("Model trained and saved successfully.")
