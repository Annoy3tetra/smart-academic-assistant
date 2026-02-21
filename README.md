🎓 Smart Academic Assistant

> A Professional Web Application for Student 360° Monitoring & Performance Prediction
Built for Hackathons & Academic Projects




---

📌 Project Overview (What Is This Project?)

Smart Academic Assistant is an intelligent web platform that monitors students’ academic performance and uses Machine Learning (ML) to predict future marks.

The main goal of this project is to provide students with Risk Analysis based on their attendance, sessional marks, and study patterns, so they can improve before exams. It includes separate panels for Admin (Teachers) and Students.


---

🚀 Key Features (What Does It Include?)

1. 🔐 Secure Authentication (Login/Signup)

Role-Based Access: Separate login for Teachers (Admin) and Students.

Firebase Auth: Secure and fast authentication system.


2. 📊 Student Dashboard

Performance Graphs: Visual representation of marks and attendance.

Risk Analysis: ML model classifies students into "High Risk", "Medium Risk", or "Low Risk" categories.

Recent Predictions: History of previous predictions.


3. 🤖 AI Performance Predictor (Machine Learning)

Prediction Engine: Uses a Linear Regression model from Scikit-Learn.

Inputs: Sessional Marks, Attendance, and Syllabus Coverage.

Output: Expected Final Exam Score and Pass/Fail Probability.


4. 📚 Course & Resource Management

Admin Panel: Teachers can add new courses, YouTube links, and topics.

Student View: Students can access subject-wise resources.



---

🛠️ Technology Stack (Technologies Used)

Component	Technology Used	Description

Frontend	HTML5, CSS3, JavaScript	Simple and responsive UI (no complex framework required).
Backend	Python (FastAPI)	High-performance API server.
Database	Firebase Firestore	Real-time NoSQL cloud database.
Authentication	Firebase Authentication	Secure user management.
ML Engine	Scikit-Learn	Performance prediction model.



---

⚙️ Installation & Setup (How to Run the Project)

Prerequisites:

Python 3.8+ installed

VS Code (recommended)


Step 1: Clone or Download the Project

Open the project folder in VS Code.

Step 2: Create a Virtual Environment

python -m venv venv

# For Windows:
.\venv\Scripts\activate

# For Mac/Linux:
# source venv/bin/activate

Step 3: Install Dependencies

pip install -r requirements.txt

Step 4: Setup Firebase Key

Create your Firebase project.

Download the serviceAccountKey.json file and paste it in the root folder (and inside the frontend/ folder).


Step 5: Run the Server

cd frontend
uvicorn server:app --reload

Note: frontend/server.py contains the main backend logic.

Step 6: Access the Application

Open in your browser:

Login Page: http://127.0.0.1:8000/login.html

API Docs: http://127.0.0.1:8000/docs (Swagger UI for testing APIs)



---

🧠 Machine Learning Model (How It Works)

The model is trained on user data:

1. Training Script: backend/ml/train_model.py


2. Algorithm: Linear Regression


3. Logic:
Higher Attendance + Higher Sessional Marks = Better Final Score



To retrain the model:

cd backend/ml
python train_model.py


---

📂 Project Structure (Folder Explanation)

smart-academic-assistant/
│
├── frontend/             
│   ├── index.html        
│   ├── dashboard.html    
│   ├── admin_dashboard.html 
│   ├── server.py         
│   └── ...
│
├── backend/              
│   ├── ml/               
│   └── app/              
│
├── requirements.txt      
└── README.md


---

🤝 Contribution

You can extend this project by adding features such as:

Assignment upload functionality

Chatbot integration using OpenAI/Gemini

Email notifications for low attendance



---

Made for Hackathons & Learning.
