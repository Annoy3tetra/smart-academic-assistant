# Smart Academic Assistant - Project Flow (Hinglish)

## 1. Big Picture Architecture
- Yeh project hybrid hai:  
  - `frontend/` mostly Firebase Auth + Firestore pe run karta hai  
  - `backend/app/` FastAPI APIs deta hai (prediction, placement readiness, course recommendation, RAG query)
  - `RAG MODEL/` alag ML + RAG assets aur scripts hold karta hai
- Data 2 jagah store hota hai:
  - Firebase Firestore (live app data)
  - PostgreSQL (via SQLAlchemy models + Alembic)

## 2. Entry Flow (User App Start)
1. User `frontend/login.html` pe login/signup karta hai (Firebase Auth).
2. Signup ke time `users/{uid}` doc Firestore me create hota hai with `name/email/role`.
3. Login ke baad `frontend/index.html` role check karta hai:
   - admin/prof/hod => `frontend/admin/index.html`
   - baaki => `frontend/student-dashboard.html`

## 3. Student Side Flow

### 3.1 Main Container
- `frontend/student-dashboard.html` sidebar + iframe shell hai.
- Default page: `dashboard-home.html`.
- Sidebar pages:
  - Dashboard
  - Performance AI (`predict.html`)
  - Placement Track (`placement.html`)
  - Course Guide (`course_guide.html`)
  - Notifications (`notifications.html`)
  - RAG Assistant (`rag-assistant.html`)

### 3.2 Dashboard Home (`frontend/dashboard-home.html`)
1. Firebase user detect hota hai.
2. Firestore `users/{uid}` se:
   - user name
   - subject marks
   load hote hain.
3. Subject marks save hone pe:
   - `users/{uid}.subject_marks` update hota hai.
   - API call `POST /students/recommend-courses` hoti hai.
4. Recommendation backend se aake UI cards me render hoti hai.
5. Latest prediction Firestore `predictions` collection se uthta hai aur top cards update hote hain.

### 3.3 Performance Prediction (`frontend/predict.html`)
1. Student subject names + marks + attendance fill karta hai.
2. API call: `POST /students/predict-direct`
3. Backend return karta hai:
   - average score
   - predicted score
   - risk level
   - placement readiness
4. Response Firestore `predictions` collection me save hota hai.
5. Subject marks bhi `users/{uid}` me sync ho jate hain.

### 3.4 Placement Tracker (`frontend/placement.html`)
- Yeh page majorly Firestore-based self-tracking system hai:
  - tasks
  - applications
  - skill matrix
  - activity log
  - notes
- `users/{uid}.placement_tracker` me auto-save hota rehta hai.
- Benchmark comparison local CSV (`RAG MODEL/ml/datasets/demo_student_dataset.csv`) read karke karta hai.

### 3.5 Course Guide (`frontend/course_guide.html`)
- Firestore `courses` collection read hoti hai.
- Admin/HOD jo courses add karta hai, student side pe yahin show hote hain.

### 3.6 Notifications (`frontend/notifications.html`)
- `users/{uid}.hod_note` realtime listener se load hota hai.
- HOD note update hote hi student ko live dikhai deta hai.

### 3.7 RAG Assistant (`frontend/rag-assistant.html`)
1. Query bheji jati hai API pe: `POST /students/rag-query`
2. Backend dynamic import se `RAG MODEL/ml/rag/rag_engine.py` load karta hai.
3. RAG pipeline context retrieve karke Gemini se answer banata hai.
4. Answer UI me show hota hai.

## 4. Admin/HOD Flow (`frontend/admin/index.html`)
1. Firebase role verify hota hai (`admin`/`hod` required).
2. Parallel Firestore reads:
   - `users`
   - `predictions`
   - `courses`
3. Dashboard KPIs calculate hote hain:
   - total students
   - average marks
   - high risk count
   - ready for placement count
4. Admin actions:
   - student detail inspect
   - role update
   - HOD note save to `users/{uid}.hod_note`
   - course resource add/delete in `courses`
   - CSV export

## 5. Backend API Flow (`backend/app`)

### 5.1 App Boot
- `backend/app/main.py` FastAPI app banata hai.
- CORS localhost/127.0.0.1 ke liye enabled hai.
- Router include: `app.api.v1.user`.

### 5.2 Core Layers
- Config: `backend/app/core/config.py`  
  - `DATABASE_URL` env se load hota hai aur PostgreSQL URL required hai.
- DB: `backend/app/core/database.py`  
  - engine, session, Base.
- Security: `backend/app/core/security.py`  
  - bcrypt hash/verify
  - JWT token create/validate

### 5.3 Main API Endpoints (Prefix: `/students`)
- Basic create/read:
  - `POST /` create student
  - `POST /subjects`
  - `POST /marks`
  - `POST /attendance`
  - `POST /users`
  - `GET /`
  - `GET /{student_id}/marks`
- Auth:
  - `POST /login` (OAuth2 form, JWT issue)
- Prediction:
  - `GET /{student_id}/predict` (admin only)
  - `GET /predict-all`
  - `POST /predict-direct`
- Placement:
  - `GET /{student_id}/placement-readiness`
- Course recommendation:
  - `POST /recommend-courses`
- RAG:
  - `POST /rag-query`

### 5.4 Prediction Logic
- `performance_predictor.py`:
  - model file: `backend/ml/saved_models/performance_model.pkl`
  - input: avg score + attendance + total subjects
  - output: predicted score + risk (`LOW/MEDIUM/HIGH`)
- `placement_model.py`:
  - risk + score + attendance se readiness (`READY/MODERATE/NOT READY`)
- `course_recommender.py`:
  - Gemini key ho to Gemini recommendations
  - warna heuristic fallback recommendations

## 6. RAG Module Flow (`RAG MODEL/ml/rag`)
1. `build_index.py` knowledge base text ko chunks me split karta hai (`###` separator).
2. SentenceTransformer embeddings banata hai.
3. `NearestNeighbors` model train + save:
   - `nn_model.pkl`
   - `chunks.npy`
4. `rag_engine.py` runtime pe:
   - query embed karta hai
   - nearest chunk retrieve karta hai
   - Gemini prompt banake answer return karta hai.

## 7. Training/Offline Scripts Flow
- `backend/ml/train_model.py`:
  - synthetic dataset banata hai
  - linear regression train karta hai
  - `performance_model.pkl` save karta hai
- `RAG MODEL/ml/generate_dataset.py`:
  - demo placement dataset create karta hai
- `RAG MODEL/ml/training_pipeline.py`:
  - random forest models train karta hai
  - `performance.pkl`, `placement.pkl`, `recommendation.pkl`, encoders save karta hai
- `RAG MODEL/ml/predict.py`:
  - saved models se demo student ke predictions nikalta hai

## 8. Database + Collections Map

### Firestore Collections
- `users/{uid}`:
  - role, name, subject_marks, placement_tracker, hod_note, etc.
- `predictions`:
  - prediction run history (predicted_score/risk/readiness/input)
- `courses`:
  - admin-added learning resources

### SQL Tables (Alembic + SQLAlchemy)
- users
- students
- subjects
- marks
- attendances
- predictions

## 9. Real User Journey (End-to-End)
1. Student signup/login karta hai (Firebase).
2. Student marks bhar ke `predict.html` se API prediction chalata hai.
3. Prediction Firestore me store hota hai.
4. `dashboard-home.html` latest prediction + readiness + recommendations dikhata hai.
5. HOD admin panel se risk students monitor karta hai.
6. HOD note bhejta hai -> student notifications me realtime dikhta hai.
7. Student RAG assistant me topic puchta hai -> backend retrieval + Gemini se answer milta hai.
