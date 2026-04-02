"""
Tests for Mergington High School Activities API

This module contains comprehensive tests for the FastAPI application,
using the AAA (Arrange-Act-Assert) pattern for clarity and maintainability.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """
    Fixture: Provides a TestClient instance for making requests to the app.
    """
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """
    Fixture: Resets activities to initial state before each test.
    Ensures tests don't interfere with each other.
    """
    from src.app import activities
    
    # Store original state
    original_state = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test
    activities.clear()
    for name, activity in original_state.items():
        activities[name] = activity


class TestRootEndpoint:
    """Tests for GET / endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """
        Test that GET / redirects to /static/index.html
        
        Arrange: Create a test client
        Act: Send a GET request to /
        Assert: Verify redirect status code (307) and Location header
        """
        # Arrange
        # client is provided by fixture
        
        # Act
        response = client.get("/", follow_redirects=False)
        
        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """
        Test that GET /activities returns all 3 activities with correct structure
        
        Arrange: Create a test client
        Act: Send a GET request to /activities
        Assert: Verify status 200, response contains all activities with required fields
        """
        # Arrange
        # client is provided by fixture
        expected_activities = ["Chess Club", "Programming Class", "Gym Class"]
        
        # Act
        response = client.get("/activities")
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert isinstance(data, dict)
        assert len(data) == 3
        
        # Verify all activities are present
        for activity_name in expected_activities:
            assert activity_name in data
        
        # Verify activity structure
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """
        Test successful signup for an existing activity
        
        Arrange: Create a test client with valid activity name and email
        Act: Send POST request to signup endpoint
        Assert: Verify status 200, success message, and participant added to activity
        """
        # Arrange
        activity_name = "Chess Club"
        email = "test.student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify participant was actually added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_signup_invalid_activity(self, client):
        """
        Test signup for non-existent activity returns 404 error
        
        Arrange: Create a test client with invalid activity name
        Act: Send POST request with invalid activity
        Assert: Verify status 404 and error message
        """
        # Arrange
        invalid_activity = "Non-Existent Activity"
        email = "test.student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{invalid_activity}/signup",
            params={"email": email}
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 404
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_participant(self, client, reset_activities):
        """
        Test that signing up the same email twice adds duplicate participant
        
        Arrange: Sign up a student once, prepare the same email for second signup
        Act: Send POST request with same email to same activity again
        Assert: Verify second signup succeeds and participant appears twice
        """
        # Arrange
        activity_name = "Programming Class"
        email = "duplicate@mergington.edu"
        
        # Sign up once
        response1 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Act: Sign up again with same email
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        data = response2.json()
        
        # Assert: Second signup succeeds (API doesn't prevent duplicates currently)
        assert response2.status_code == 200
        
        # Verify duplicate entry exists
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        participant_count = activities_data[activity_name]["participants"].count(email)
        assert participant_count == 2
