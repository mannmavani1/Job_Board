import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# --- IMPORTS ---
# Ensure you run this from the project root using: python -m pytest app/tests.py
from app.main import app
from app.database.session import get_session

# ==========================================
# 1. CONFIGURATION & FIXTURES
# ==========================================

TEST_DATABASE_URL = "sqlite:///:memory:"

# StaticPool ensures the in-memory DB is shared across the same thread
engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture():
    """Creates a fresh database for every test function."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Overrides the database dependency to use the test database."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

# --- Auth Helpers ---
def get_auth_headers(client, email, password, role):
    # Try register (ignore if exists)
    client.post("/auth/register", json={
        "email": email, "password": password, "role": role
    })
    # Login
    response = client.post("/auth/login", json={
        "email": email, "password": password
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def recruiter_headers(client):
    return get_auth_headers(client, "recruiter@test.com", "password123", "recruiter")

@pytest.fixture
def recruiter_2_headers(client):
    return get_auth_headers(client, "recruiter2@test.com", "password123", "recruiter")

@pytest.fixture
def seeker_headers(client):
    return get_auth_headers(client, "seeker@test.com", "password123", "job_seeker")


# ==========================================
# 2. AUTHENTICATION TESTS
# ==========================================

def test_register_user(client):
    res = client.post("/auth/register", json={
        "email": "new@test.com", "password": "password123", "role": "job_seeker"
    })
    assert res.status_code == 201
    assert res.json()["email"] == "new@test.com"
    assert "password" not in res.json()

def test_register_duplicate_email(client):
    payload = {"email": "dup@test.com", "password": "password123", "role": "recruiter"}
    client.post("/auth/register", json=payload)
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 400
    assert "Email already registered" in res.json()["detail"]

def test_login_success(client):
    client.post("/auth/register", json={"email": "login@test.com", "password": "password123", "role": "recruiter"})
    res = client.post("/auth/login", json={"email": "login@test.com", "password": "password123"})
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_login_invalid_credentials(client):
    client.post("/auth/register", json={"email": "valid@test.com", "password": "password123", "role": "recruiter"})
    res = client.post("/auth/login", json={"email": "valid@test.com", "password": "WRONG_PASSWORD"})
    assert res.status_code == 401

# ==========================================
# 3. COMPANY TESTS
# ==========================================

def test_create_company_success(client, recruiter_headers):
    res = client.post("/companies", json={"name": "Tech Co", "location": "NY"}, headers=recruiter_headers)
    assert res.status_code == 201
    assert res.json()["name"] == "Tech Co"

def test_create_company_forbidden_for_seeker(client, seeker_headers):
    res = client.post("/companies", json={"name": "Hack Co"}, headers=seeker_headers)
    assert res.status_code == 403

def test_update_company_ownership(client, recruiter_headers, recruiter_2_headers):
    create_res = client.post("/companies", json={"name": "R1 Co"}, headers=recruiter_headers)
    company_id = create_res.json()["id"]

    update_res = client.put(f"/companies/{company_id}", json={"name": "Stolen Co"}, headers=recruiter_2_headers)
    assert update_res.status_code == 403

def test_get_company_not_found(client, recruiter_headers):
    res = client.get("/companies/9999", headers=recruiter_headers)
    assert res.status_code == 404

def test_delete_company(client, recruiter_headers):
    create_res = client.post("/companies", json={"name": "Del Co"}, headers=recruiter_headers)
    cid = create_res.json()["id"]
    del_res = client.delete(f"/companies/{cid}", headers=recruiter_headers)
    assert del_res.status_code == 204
    get_res = client.get(f"/companies/{cid}", headers=recruiter_headers)
    assert get_res.status_code == 404

# ==========================================
# 4. JOB TESTS
# ==========================================

@pytest.fixture
def setup_company(client, recruiter_headers):
    res = client.post("/companies", json={"name": "Job Co"}, headers=recruiter_headers)
    return res.json()["id"]

def test_create_job_success(client, recruiter_headers, setup_company):
    job_data = {
        "title": "Python Dev",
        "description": "Backend",
        "job_type": "full_time",
        "experience_level": "mid",
        "company_id": setup_company
    }
    res = client.post("/jobs", json=job_data, headers=recruiter_headers)
    assert res.status_code == 201
    assert res.json()["title"] == "Python Dev"

def test_job_search_filters(client, recruiter_headers, setup_company):
    client.post("/jobs", json={"title": "Python Dev", "description": "A", "job_type": "full_time", "experience_level": "mid", "company_id": setup_company}, headers=recruiter_headers)
    client.post("/jobs", json={"title": "React Dev", "description": "B", "job_type": "part_time", "experience_level": "senior", "company_id": setup_company}, headers=recruiter_headers)

    res = client.get("/jobs?q=Python")
    assert res.json()["count"] == 1
    assert res.json()["results"][0]["title"] == "Python Dev"

    res = client.get("/jobs?job_type=part_time")
    assert res.json()["count"] == 1
    assert res.json()["results"][0]["title"] == "React Dev"

def test_update_job_permissions(client, recruiter_headers, recruiter_2_headers, setup_company):
    res = client.post("/jobs", json={"title": "My Job", "description": "desc", "job_type": "remote", "experience_level": "mid", "company_id": setup_company}, headers=recruiter_headers)
    job_id = res.json()["id"]

    res = client.put(f"/jobs/{job_id}", json={"title": "Hacked"}, headers=recruiter_2_headers)
    assert res.status_code == 403

def test_delete_job_soft_delete(client, recruiter_headers, setup_company):
    res = client.post("/jobs", json={"title": "Temp Job", "description": "desc", "job_type": "remote", "experience_level": "mid", "company_id": setup_company}, headers=recruiter_headers)
    job_id = res.json()["id"]

    client.delete(f"/jobs/{job_id}", headers=recruiter_headers)
    res = client.get(f"/jobs/{job_id}")
    assert res.status_code == 404

# ==========================================
# 5. TAG TESTS
# ==========================================

def test_tags_operations(client, recruiter_headers, setup_company):
    # 1. Create Tag
    tag_res = client.post("/tags", json={"name": "Python", "description": "Lang"}, headers=recruiter_headers)
    assert tag_res.status_code == 201
    tag_id = tag_res.json()["id"]

    # 2. Attach to Job
    job_res = client.post("/jobs", json={"title": "Tagged Job", "description": "x", "job_type": "remote", "experience_level": "mid", "company_id": setup_company}, headers=recruiter_headers)
    job_id = job_res.json()["id"]

    attach_res = client.post(f"/jobs/{job_id}/tags", json=[tag_id], headers=recruiter_headers)
    assert attach_res.status_code == 201

    # 3. List Job Tags
    list_res = client.get(f"/jobs/{job_id}/tags")
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["name"] == "Python"

# ==========================================
# 6. APPLICATION TESTS
# ==========================================

@pytest.fixture
def setup_job(client, recruiter_headers, setup_company):
    res = client.post("/jobs", json={"title": "App Job", "description": "desc", "job_type": "remote", "experience_level": "mid", "company_id": setup_company}, headers=recruiter_headers)
    return res.json()["id"]

def test_apply_job_success(client, seeker_headers, setup_job):
    payload = {"resume_url": "http://resume.com", "cover_letter": "Hire me"}
    res = client.post(f"/applications/jobs/{setup_job}/apply", json=payload, headers=seeker_headers)
    assert res.status_code == 201
    assert res.json()["status"] == "applied"

def test_recruiter_cannot_apply(client, recruiter_headers, setup_job):
    payload = {"resume_url": "http://resume.com"}
    res = client.post(f"/applications/jobs/{setup_job}/apply", json=payload, headers=recruiter_headers)
    assert res.status_code == 403

def test_duplicate_application(client, seeker_headers, setup_job):
    payload = {"resume_url": "http://resume.com"}
    client.post(f"/applications/jobs/{setup_job}/apply", json=payload, headers=seeker_headers)
    res = client.post(f"/applications/jobs/{setup_job}/apply", json=payload, headers=seeker_headers)
    assert res.status_code == 400
    assert "already applied" in res.json()["detail"]

def test_job_seeker_withdraw(client, seeker_headers, setup_job):
    res = client.post(f"/applications/jobs/{setup_job}/apply", json={"resume_url": "url"}, headers=seeker_headers)
    app_id = res.json()["id"]
    
    del_res = client.delete(f"/applications/{app_id}", headers=seeker_headers)
    assert del_res.status_code == 204

def test_recruiter_update_status(client, recruiter_headers, seeker_headers, setup_job):
    res = client.post(f"/applications/jobs/{setup_job}/apply", json={"resume_url": "url"}, headers=seeker_headers)
    app_id = res.json()["id"]

    status_res = client.put(f"/applications/{app_id}/status", json={"status": "hired"}, headers=recruiter_headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "hired"

def test_recruiter_view_applications(client, recruiter_headers, seeker_headers, setup_job):
    client.post(f"/applications/jobs/{setup_job}/apply", json={"resume_url": "url"}, headers=seeker_headers)
    
    res = client.get(f"/jobs/{setup_job}/applications", headers=recruiter_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

def test_seeker_cannot_update_status(client, seeker_headers, setup_job):
    res = client.post(f"/applications/jobs/{setup_job}/apply", json={"resume_url": "url"}, headers=seeker_headers)
    app_id = res.json()["id"]

    res = client.put(f"/applications/{app_id}/status", json={"status": "hired"}, headers=seeker_headers)
    assert res.status_code == 403

def test_withdraw_hired_application_fails(client, recruiter_headers, seeker_headers, setup_job):
    res = client.post(f"/applications/jobs/{setup_job}/apply", json={"resume_url": "url"}, headers=seeker_headers)
    app_id = res.json()["id"]

    client.put(f"/applications/{app_id}/status", json={"status": "hired"}, headers=recruiter_headers)

    res = client.delete(f"/applications/{app_id}", headers=seeker_headers)
    assert res.status_code == 400
    assert "Cannot withdraw a hired application" in res.json()["detail"]