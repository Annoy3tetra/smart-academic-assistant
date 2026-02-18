import os
import pandas as pd
import pickle

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


# ==============================
# 1. Load Dataset
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(BASE_DIR, "datasets", "demo_student_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")


df = pd.read_csv(DATA_PATH)

# ==============================
# 2. Encode Categorical Columns
# ==============================

label_encoders = {}

categorical_columns = ["preferred_domain", "performance_label", "placement_label"]

for col in categorical_columns:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    label_encoders[col] = le

# ==============================
# 3. Define Features & Targets
# ==============================

X = df.drop(["student_id", "performance_label", "placement_label"], axis=1)

y_performance = df["performance_label"]
y_placement = df["placement_label"]
y_recommendation = df["preferred_domain"]


# ==============================
# 4. Train-Test Split
# ==============================

X_train, X_test, y_perf_train, y_perf_test = train_test_split(
    X, y_performance, test_size=0.2, random_state=42
)

_, _, y_place_train, y_place_test = train_test_split(
    X, y_placement, test_size=0.2, random_state=42
)

_, _, y_reco_train, y_reco_test = train_test_split(
    X, y_recommendation, test_size=0.2, random_state=42
)


# ==============================
# 5. Train Models
# ==============================

performance_model = RandomForestClassifier(random_state=42)
placement_model = RandomForestClassifier(random_state=42)
recommendation_model = RandomForestClassifier(random_state=42)


performance_model.fit(X_train, y_perf_train)
placement_model.fit(X_train, y_place_train)
recommendation_model.fit(X_train, y_reco_train) # simple placeholder

# ==============================
# 6. Evaluate Models
# ==============================

perf_pred = performance_model.predict(X_test)
place_pred = placement_model.predict(X_test)
reco_pred = recommendation_model.predict(X_test)

print("Performance Model Accuracy:",
      accuracy_score(y_perf_test, perf_pred))

print("Placement Model Accuracy:",
      accuracy_score(y_place_test, place_pred))

print("Recommendation Model Accuracy:",
      accuracy_score(y_reco_test, reco_pred))

# ==============================
# 7. Feature Importance
# ==============================

importances = performance_model.feature_importances_
feature_names = X.columns

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": importances
}).sort_values(by="Importance", ascending=False)

print("\n🔎 Feature Importance (Performance Model):")
print(feature_importance_df)

# ==============================
# 6. Create saved_models Folder if not exists
# ==============================

os.makedirs(MODEL_DIR, exist_ok=True)

# ==============================
# 7. Save Models
# ==============================

with open(os.path.join(MODEL_DIR, "performance.pkl"), "wb") as f:
    pickle.dump(performance_model, f)

with open(os.path.join(MODEL_DIR, "placement.pkl"), "wb") as f:
    pickle.dump(placement_model, f)

with open(os.path.join(MODEL_DIR, "recommendation.pkl"), "wb") as f:
    pickle.dump(recommendation_model, f)

print("✅ Models trained and saved successfully!")

# ==============================
# 8. Save Label Encoders
# ==============================

with open(os.path.join(MODEL_DIR, "label_encoders.pkl"), "wb") as f:
    pickle.dump(label_encoders, f)

print("✅ Encoders saved successfully!")
