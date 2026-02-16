"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        key: {
            "description": value["description"],
            "schedule": value["schedule"],
            "max_participants": value["max_participants"],
            "participants": value["participants"].copy()
        }
        for key, value in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for key, value in original_activities.items():
        activities[key]["participants"] = value["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static HTML"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the get activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that get_activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check structure of an activity
        first_activity = next(iter(data.values()))
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that specific activities are present"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = [
            "Basketball",
            "Tennis Club",
            "Art Studio",
            "Drama Club",
            "Debate Team",
            "Science Club",
            "Chess Club",
            "Programming Class",
            "Gym Class"
        ]
        
        for activity in expected_activities:
            assert activity in data


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball/signup?email=newstudent@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "newstudent@mergington.edu" in activities["Basketball"]["participants"]
    
    def test_signup_duplicate_student(self, client, reset_activities):
        """Test that duplicate signups are prevented"""
        email = "test@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/Basketball/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/Basketball/signup?email={email}"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for a nonexistent activity"""
        response = client.post(
            "/activities/NonexistentActivity/signup?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_multiple_students_same_activity(self, client, reset_activities):
        """Test that multiple students can sign up for same activity"""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for student in students:
            response = client.post(
                f"/activities/Basketball/signup?email={student}"
            )
            assert response.status_code == 200
        
        # Verify all were added
        for student in students:
            assert student in activities["Basketball"]["participants"]


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        email = "test@mergington.edu"
        
        # First signup
        client.post(f"/activities/Basketball/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/Basketball/unregister?email={email}"
        )
        
        assert response.status_code == 200
        assert "unregistered" in response.json()["message"].lower()
        
        # Verify participant was removed
        assert email not in activities["Basketball"]["participants"]
    
    def test_unregister_nonexistent_student(self, client, reset_activities):
        """Test unregistering a student who isn't signed up"""
        response = client.delete(
            "/activities/Basketball/unregister?email=nonexistent@mergington.edu"
        )
        
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from a nonexistent activity"""
        response = client.delete(
            "/activities/NonexistentActivity/unregister?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_multiple_students(self, client, reset_activities):
        """Test that removing one student doesn't affect others"""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        # Sign up all students
        for student in students:
            client.post(f"/activities/Basketball/signup?email={student}")
        
        # Unregister one student
        response = client.delete(
            f"/activities/Basketball/unregister?email={students[1]}"
        )
        assert response.status_code == 200
        
        # Verify only one was removed
        assert students[0] in activities["Basketball"]["participants"]
        assert students[1] not in activities["Basketball"]["participants"]
        assert students[2] in activities["Basketball"]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity limits"""
    
    def test_activity_has_max_participants(self, client):
        """Test that activities have max_participants property"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert activity["max_participants"] > 0
            # Current participants should not exceed max
            assert len(activity["participants"]) <= activity["max_participants"]
