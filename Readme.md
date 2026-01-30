# 🚀 Job Board API + AI Intelligence Layer

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-green)
![SQLModel](https://img.shields.io/badge/SQLModel-0.0.8-red)
![License](https://img.shields.io/badge/License-MIT-grey)

A production-ready RESTful API built with **FastAPI** and **SQLModel**. This platform facilitates the hiring process by allowing Recruiters to post jobs, manage company profiles, and collaborate with teams, while Job Seekers can search for positions and track their applications.

---

## 🌟 Key Features

### 🔐 Authentication & Security
* **JWT Authentication:** Secure login and registration flows.
* **Role-Based Access Control (RBAC):** Strict separation between `Recruiter` and `Job Seeker` permissions.
* **Security:** Password hashing using Bcrypt and secure headers middleware.

### 🏢 Company Management
* **Profile Management:** Recruiters can create and update company details.
* **Team Collaboration:** **(New)** Company owners can invite other recruiters to manage the company and post jobs using the `POST /companies/{id}/recruiters` endpoint.

### 💼 Job Management
* **Job Posting:** Recruiters can create job listings linked to their companies.
* **Smart Validation:** Logic ensures business rules (e.g., Salary Min < Salary Max).
* **Advanced Search:** Filter jobs by keyword, location, type (Remote/On-site), and experience level.
* **Tagging System:** Categorize jobs with specific tech tags (e.g., Python, React).

### 📝 Application Tracking
* **Application Flow:** Seekers can apply with a Resume URL and Cover Letter.
* **Duplicate Prevention:** Logic prevents candidates from applying to the same job twice.
* **Status Updates:** Recruiters can track candidates through the pipeline (`Applied` → `Shortlisted` → `Hired`).


### 🤖 AI Application Layer
* **Ask-AI:** A Rag Based Q&A Where You can Ask anything about the data Stored about Company,Job,Application etc.
* **Improve Job-description:** A Feature where you pass old job-description and and give mode (short,marketing and detailed)
* **Recommend-Job:** A feature where you provide your Resume Text and based on that we will Recommend Jobs 


---

## 🛠️ Tech Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Database:** PostgreSQL+ChromaDB
* **ORM:** [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic)
* **Server:** Uvicorn
* **Testing:** Pytest
* **AI Model:** llama-3.3-70b-versatile

---

## 🚀 Getting Started
### Mac/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```
### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Environment Variables

JWT_SECRET_KEY="your_super_secret_key"
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=""
GROQ_API_KEY=""

### Run the Application
```bash
python -m uvicorn main:app --reload
```

## 📂 Project Structure
```text
Job_Board/
├── app/
│   ├── ai/             # Configuration of llm and vector store
│   ├── core/           # Configuration & Security settings
│   ├── database/       # Database connection & Session logic
│   ├── dependencies/   # Auth dependencies & RBAC
│   ├── models/         # SQLModel Database Tables
│   ├── routers/        # API Routes (Auth, Jobs, Companies, AI etc.)
│   ├── schemas/        # Pydantic Schemas for Request/Response
│   └── tests.py        # Automated Test Suite
├── main.py             # Application Entry Point
├── requirements.txt    # Python Dependencies
└── README.md           # Project Documentation
```

