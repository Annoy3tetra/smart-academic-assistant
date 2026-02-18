# 🎓 Smart Academic Assistant

> **A Professional Web Application for Student 360° Monitoring & Performance Prediction**
> _Built for Hackathons & Academic Projects_

## 📌 Project Overview (Project Kya Hai?)
**Smart Academic Assistant** ek intelligent web platform hai jo students ki academic performance ko monitor karta hai aur Machine Learning (ML) ka use karke future marks predict karta hai.

Is project ka main goal students ko unki **attendance**, **sessional marks**, aur **study patterns** ke basis par "Risk Analysis" dena hai taaki wo exams se pehle improve kar sakein. Isme **Admin (Teachers)** aur **Student** panels alag-alag hain.

---

## 🚀 Key Features (Isme Kya Kya Hai?)

### 1. 🔐 Secure Authentication (Login/Signup)
- **Role-Based Access:** Teachers (Admin) aur Students ke liye alag login.
- **Firebase Auth:** Secure aur fast login system.

### 2. 📊 Student Dashboard
- **Performance Graphs:** Apne marks aur attendance ka graphical view.
- **Risk Analysis:** ML model batata hai ki aap "High Risk", "Medium Risk" ya "Low Risk" zone mein hain.
- **Recent Predictions:** Purane predictions ki history.

### 3. 🤖 AI Performance Predictor (Machine Learning)
- **Prediction Engine:** `Scikit-Learn` ka Linear Regression model use hota hai.
- **Inputs:** Sessional Marks, Attendance, aur Syllabus Coverage.
- **Output:** Expected Final Exam Score & Pass/Fail Probability.

### 4. 📚 Course & Resource Management
- **Admin Panel:** Teachers naye courses, YouTube links, aur topics add kar sakte hain.
- **Student View:** Students subjects wise resources access kar sakte hain.

---

## 🛠️ Technology Stack (Kaunsi Technologies Use Hui Hain?)

| Component | Technology Used | Description |
|-----------|----------------|-------------|
| **Frontend** | HTML5, CSS3, JavaScript | Simple & Responsive UI (No complex framework needed). |
| **Backend** | Python (FastAPI) | High-performance API server. |
| **Database** | Firebase Firestore | Real-time NoSQL cloud database. |
| **Auth** | Firebase Authentication | Secure user management. |
| **ML Engine** | Scikit-Learn | Performance prediction model. |

---

## ⚙️ Installation & Setup (Project Kaise Run Karein?)

Follow these simple steps to run the project on your laptop:

### Prerequisites:
- Python 3.8+ installed.
- VS Code (Recommended).

### Step 1: Clone or Download Project
Is folder ko VS Code mein open karein.

### Step 2: Create Virtual Environment
Terminal mein yeh commands run karein:
```bash
python -m venv venv
# Windows ke liye activate command:
.\venv\Scripts\activate
# Mac/Linux ke liye:
# source venv/bin/activate
```

### Step 3: Install Dependencies
Sabhi libraries install karne ke liye:
```bash
pip install -r requirements.txt
```

### Step 4: Setup Firebase Key
- Apna Firebase project banayein.
- `serviceAccountKey.json` file download karein aur root folder (aur `frontend/` folder) mein paste karein.

### Step 5: Run the Server
Backend server start karne ke liye:
```bash
cd frontend
uvicorn server:app --reload
```
_Note: Hum `frontend/server.py` use kar rahe hain kyunki wahi main backend logic hold kar raha hai._

### Step 6: Access Application
Browser mein open karein:
- **Login Page:** http://127.0.0.1:8000/login.html
- **API Docs:** http://127.0.0.1:8000/docs (Swagger UI for testing APIs)

---

## 🧠 Machine Learning Model (Kaise Kaam Karta Hai?)
Model users ke data par train hota hai:
1. **Training Script:** `backend/ml/train_model.py`
2. **Algorithm:** Linear Regression.
3. **Logic:**
   - Higher Attendance + Higher Sessional Marks = **Better Final Score**.

Agar model retrain karna ho:
```bash
cd backend/ml
python train_model.py
```

---

## 📂 Project Structure (Folders Ka Matlab)
 
```
smart-academic-assistant/
│
├── frontend/             # 🎨 Main UI & Server Logic
│   ├── index.html        # Home Page
│   ├── dashboard.html    # Student Dashboard
│   ├── admin_dashboard.html # Teacher Dashboard
│   ├── server.py         # 🚀 Main FastAPI Backend File
│   └── ...
│
├── backend/              # 🧠 ML & Alternative Logic
│   ├── ml/               # Machine Learning Models
│   └── app/              # (Alternative Backend Structure)
│
├── requirements.txt      # 📦 List of Libraries
└── README.md             # 📖 This Documentation
```

---

## 🤝 Contribution
Aap isme aur features add kar sakte hain jaise:
- Assignments upload feature.
- Chatbot integration using OpenAI/Gemini.
- Email notifications for low attendance.

---
**Made with ❤️ for Hackathons & Learning!**
