from datetime import datetime,timedelta
import pytest
from app import app, mongo

# Test Client Fixture
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['MONGO_URI'] = "mongodb+srv://faiqanasir60:Cv6Ww5mwwMYoO3Rf@spotifycluster.bxgjx.mongodb.net/evote?retryWrites=true&w=majority&appName=SpotifyCluster"
    app.config["MONGO_DBNAME"] = "evote"
    with app.test_client() as client:
        with app.app_context():
            mongo.db.voters.delete_many({})
            mongo.db.candidates.delete_many({})
            mongo.db.elections.delete_many({})
            mongo.db.admins.delete_many({})
            mongo.db.notifications.delete_many({})
            mongo.db.admins.insert_one({
                "admin_id": "admin",
                "name": "Admin",
                "cnic": "admin_cnic",
                "dob": "1970-01-01"
            })
        yield client


# Helper Functions
def login_admin(client):
    client.post('/login', json={"cnic": "admin_cnic", "dob": "1970-01-01"})


def login_voter(client):
    client.post('/login', json={"cnic": "12345-6789012-3", "dob": "2000-01-01"})


# Tests
def test_login_valid(client):
    mongo.db.voters.insert_one({
        "voter_id": "VOTER001",
        "name": "John Doe",
        "cnic": "12345-6789012-3",
        "dob": "2000-01-01",
        "age": 23,
        "voted": False
    })
    response = client.post('/login', json={"cnic": "12345-6789012-3", "dob": "2000-01-01"})
    assert response.status_code == 200
    assert response.json['success'] is True


def test_login_invalid(client):
    response = client.post('/login', json={"cnic": "invalid_cnic", "dob": "1900-01-01"})
    assert response.status_code == 200
    assert response.json['success'] is False


def test_voter_insertion(client):
    login_admin(client)
    response = client.post('/register_voter', json={
        "name": "John Doe",
        "cnic": "11111-1111111-1",
        "dob": "1990-01-01",
        "age": 30
    })
    assert response.status_code == 200
    assert response.json['success'] is True


def test_duplicate_voter_registration(client):
    login_admin(client)
    client.post('/register_voter', json={
        "name": "John Doe",
        "cnic": "22222-2222222-2",
        "dob": "1990-01-01",
        "age": 30
    })
    response = client.post('/register_voter', json={
        "name": "John Doe",
        "cnic": "22222-2222222-2",
        "dob": "1990-01-01",
        "age": 30
    })
    assert response.status_code == 200
    assert response.json['success'] is False
def test_notifications_on_vote_cast(client):
    # Log in as a voter and cast a vote
    login_voter(client)
    mongo.db.candidates.insert_one({"candidate_id": "CAND001", "name": "Alice", "party": "Party A"})
    mongo.db.elections.insert_one({
        "election_id": "ELECT001",
        "name": "General Elections 2024",
        "start_date": datetime.now() - timedelta(days=1),
        "end_date": datetime.now() + timedelta(days=1),
        "votes": {}
    })
    response = client.post('/cast_vote', json={
        "election_id": "ELECT001",
        "candidate_id": "CAND001"
    })
    assert response.status_code == 200
    assert response.json['success'] is True

    # Verify notification is generated
    notification = mongo.db.notifications.find_one({"recipient_id": "VOTER001"})
    assert notification is not None
    assert notification["message"] == "Your vote in election ELECT001 has been successfully cast."

def test_notification_system(client):
    login_admin(client)
    response = client.post('/send_notification', json={
        "recipient_id": "VOTER001",
        "message": "Test notification message."
    })
    assert response.status_code == 200
    assert response.json['success'] is True

    # Verify the notification is in the database
    notification = mongo.db.notifications.find_one({"recipient_id": "VOTER001"})
    assert notification is not None
    assert notification["message"] == "Test notification message."


def test_homepage_render(client):
    login_admin(client)
    response = client.get('/')
    assert response.status_code == 200


def test_form_validation(client):
    login_admin(client)
    response = client.post('/register_voter', json={
        "name": "John Doe",
        "cnic": "12345",
        "dob": "2000-01-01",
        "age": "17"  # Can be a string but convertible to an integer
    })
    assert response.status_code == 400 or (response.json and response.json['success'] is False)


def test_unauthorized_access(client):
    # Try accessing a restricted route without logging in
    response = client.get('/')
    assert response.status_code == 302  # Redirect to login page
    assert '/login_page' in response.headers['Location']  # Check if redirected to login

def login_voter(client):
    # Insert the voter into the database
    mongo.db.voters.insert_one({
        "voter_id": "VOTER001",
        "name": "John Doe",
        "cnic": "12345-6789012-3",
        "dob": "2000-01-01",
        "age": 23,
        "voted": False
    })

    # Log in the voter
    response = client.post('/login', json={
        "cnic": "12345-6789012-3",
        "dob": "2000-01-01"
    })
    assert response.status_code == 200
    assert response.json['success'] is True

def test_available_elections(client):
    # Insert a voter and log in
    mongo.db.voters.insert_one({
        "voter_id": "VOTER001",
        "name": "John Doe",
        "cnic": "12345-6789012-3",
        "dob": "2000-01-01",
        "age": 23,
        "voted": False
    })
    login_voter(client)

    # Insert an active election
    mongo.db.elections.insert_one({
        "election_id": "ELECT001",
        "name": "General Elections 2024",
        "start_date": datetime.now() - timedelta(days=1),  # Active now
        "end_date": datetime.now() + timedelta(days=1),
        "votes": {}
    })

    # Test the route
    response = client.get('/available_elections')
    assert response.status_code == 200
    assert response.json['success'] is True
    assert len(response.json['data']) > 0

def test_vote_casting(client):
    # Ensure the voter is logged in
    login_voter(client)

    # Insert a candidate
    mongo.db.candidates.insert_one({
        "candidate_id": "CAND001",
        "name": "Alice",
        "party": "Party A"
    })

    # Insert an active election
    mongo.db.elections.insert_one({
        "election_id": "ELECT001",
        "name": "General Elections 2024",
        "start_date": datetime.now() - timedelta(days=1),  # Active now
        "end_date": datetime.now() + timedelta(days=1),
        "votes": {}
    })

    # Cast a vote
    response = client.post('/cast_vote', json={
        "election_id": "ELECT001",
        "candidate_id": "CAND001"
    })
    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['message'] == "Vote cast successfully."
