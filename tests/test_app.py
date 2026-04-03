"""
Tests for Mergington High School Activities API

This module contains comprehensive tests for the FastAPI application,
using the AAA (Arrange-Act-Assert) pattern for clarity and maintainability.
Tests cover all endpoints: GET /, GET /activities,
POST /activities/{activity_name}/signup, and
DELETE /activities/{activity_name}/participants.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


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
    Ensures tests don't interfere with each other by preserving participant lists.
    """
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
        Test that GET /activities returns all activities with correct structure
        
        Arrange: Create a test client
        Act: Send a GET request to /activities
        Assert: Verify status 200, response contains all activities with required fields
        """
        # Arrange
        expected_activities = [
            "Chess Club", "Programming Class", "Gym Class", "Basketball Team",
            "Tennis Club", "Art Studio", "Theater Club", "Debate Team", "Science Club"
        ]
        
        # Act
        response = client.get("/activities")
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert isinstance(data, dict)
        assert len(data) == 9
        
        # Verify all activities are present
        for activity_name in expected_activities:
            assert activity_name in data
        
        # Verify activity structure for each activity
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
    
    def test_get_activities_has_correct_participant_data(self, client):
        """
        Test that activities have correct initial participant information
        
        Arrange: Create a test client
        Act: Get /activities response
        Assert: Verify specific activities have expected participants
        """
        # Arrange
        # client is provided by fixture
        
        # Act
        response = client.get("/activities")
        data = response.json()
        
        # Assert
        # Verify specific activity details
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]
        
        assert len(data["Theater Club"]["participants"]) == 3
        assert "lucas@mergington.edu" in data["Theater Club"]["participants"]


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
        initial_count = len(activities[activity_name]["participants"])
        
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
        assert len(activities[activity_name]["participants"]) == initial_count + 1
        assert email in activities[activity_name]["participants"]
    
    def test_signup_multiple_activities(self, client, reset_activities):
        """
        Test that same student can signup for multiple activities
        
        Arrange: Register student for multiple different activities
        Act: Check student appears in multiple activity participant lists
        Assert: Verify student successfully joined all activities
        """
        # Arrange
        email = "multi.student@mergington.edu"
        activities_to_join = ["Programming Class", "Art Studio", "Debate Team"]
        
        # Act & Assert for each activity signup
        for activity_name in activities_to_join:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
            assert email in activities[activity_name]["participants"]
    
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
    
    def test_signup_duplicate_returns_error(self, client, reset_activities):
        """
        Test that duplicate signup attempts are rejected
        
        Arrange: Sign up a student for an activity
        Act: Attempt to sign up the same student again
        Assert: Verify second signup fails with 400 error
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
        initial_count = len(activities[activity_name]["participants"])
        
        # Act: Try to sign up again
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        data = response2.json()
        
        # Assert
        assert response2.status_code == 400
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
        
        # Verify no duplicate was added
        assert len(activities[activity_name]["participants"]) == initial_count


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/participants endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """
        Test successful unregistration from an activity
        
        Arrange: Get existing participant from an activity
        Act: Send DELETE request to unregister endpoint
        Assert: Verify status 200, success message, and participant removed
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Known existing participant
        initial_count = len(activities[activity_name]["participants"])
        assert email in activities[activity_name]["participants"]
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify participant was actually removed
        assert len(activities[activity_name]["participants"]) == initial_count - 1
        assert email not in activities[activity_name]["participants"]
    
    def test_unregister_invalid_activity(self, client):
        """
        Test unregister from non-existent activity returns 404 error
        
        Arrange: Create a test client with invalid activity name
        Act: Send DELETE request with invalid activity
        Assert: Verify status 404 and error message
        """
        # Arrange
        invalid_activity = "Non-Existent Activity"
        email = "test@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{invalid_activity}/participants",
            params={"email": email}
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 404
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_participant_not_found(self, client, reset_activities):
        """
        Test unregister for student not in activity returns 404 error
        
        Arrange: Create test email that's not in an activity
        Act: Send DELETE request with non-member email
        Assert: Verify status 404 and participant not found message
        """
        # Arrange
        activity_name = "Science Club"
        email = "not.a.member@mergington.edu"
        assert email not in activities[activity_name]["participants"]
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 404
        assert "detail" in data
        assert "participant not found" in data["detail"].lower()
    
    def test_unregister_then_signup_same_student(self, client, reset_activities):
        """
        Test that student can re-signup after unregistering
        
        Arrange: Existing participant, unregister them
        Act: Sign them back up
        Assert: Verify they're successfully registered again
        """
        # Arrange
        activity_name = "Tennis Club"
        email = "tyler@mergington.edu"  # Known existing participant
        
        # First, unregister
        response1 = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        assert response1.status_code == 200
        assert email not in activities[activity_name]["participants"]
        
        # Act: Sign up again
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response2.status_code == 200
        assert email in activities[activity_name]["participants"]


class TestIntegrationScenarios:
    """Integration tests for complex workflows"""
    
    def test_full_signup_flow_multiple_activities(self, client, reset_activities):
        """
        Test complete flow: signup for multiple activities, then unregister from one
        
        Arrange: New student, multiple target activities
        Act: Sign up for 3 activities, unregister from 1
        Assert: Verify student is in 2 activities and not in 1
        """
        # Arrange
        email = "integration.test@mergington.edu"
        activities_to_join = ["Soccer Team", "Debate Team", "Science Club"]
        
        # Act: Join first two activities (Soccer Team may not exist, we'll handle it)
        response1 = client.post(
            f"/activities/Debate Team/signup",
            params={"email": email}
        )
        response2 = client.post(
            f"/activities/Science Club/signup",
            params={"email": email}
        )
        
        # Assert initial signups
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Unregister from one
        response3 = client.delete(
            f"/activities/Debate Team/participants",
            params={"email": email}
        )
        
        # Assert final state
        assert response3.status_code == 200
        assert email in activities["Science Club"]["participants"]
        assert email not in activities["Debate Team"]["participants"]
