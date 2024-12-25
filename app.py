""" 
This is the main application script for the Election Management System (EMS) 
using Flask and MongoDB. It provides various routes for user authentication, 
election management, and voting processes. 
"""

from datetime import datetime
from functools import wraps
from flask import (
    Flask, request, jsonify, render_template, session, redirect, url_for
)
from flask_pymongo import PyMongo

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'
# Configure MongoDB connection
app.config["MONGO_URI"] = (
    "mongodb+srv://bsef21m030:Alsamrym3pm@cluster0.yknic.mongodb.net/"
    "retryWrites=true&w=majority&appName=Cluster0"
)
app.config["MONGO_DBNAME"] = "evote"
mongo = PyMongo(app)

# Check MongoDB connection before each request
@app.before_request
def check_mongo_connection():
    """Ensure MongoDB connection is active before processing any request."""
    print(mongo.db)
    print(mongo.db.list_collection_names())

# Utility function to format JSON responses
def format_response(success, message, data=None):
    """Format and return a JSON response with success status, message, and optional data."""
    return jsonify({"success": success, "message": message, "data": data})

# Decorator for login required routes
def login_required(f):
    """Decorator to require user authentication for access to certain routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator for admin required routes
def admin_required(f):
    """Decorator to require admin privileges for access to certain routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'admin':
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize admin user if not exists
@app.before_request
def create_admin():
    """Create an admin user if one does not already exist in the database."""
    if not mongo.db.admins.find_one({"cnic": "admin_cnic"}):
        mongo.db.admins.insert_one({
            "admin_id": "admin",
            "name": "Admin",
            "cnic": "admin_cnic",
            "dob": "1970-01-01"
        })

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login. Authenticate and set session based on user role."""
    if request.method == 'GET':
        return render_template('login.html')  # Render login page
    data = request.json
    cnic = data.get('cnic')
    dob = data.get('dob')

    user = mongo.db.voters.find_one({"cnic": cnic, "dob": dob})
    if user:
        session['user'] = {"id": user['voter_id'], "role": "voter"}
        return format_response(True, "Login successful", {"role": "voter"})
    admin = mongo.db.admins.find_one({"cnic": cnic, "dob": dob})
    if admin:
        session['user'] = {"id": admin['admin_id'], "role": "admin"}
        return format_response(True, "Login successful", {"role": "admin"})
    return format_response(False, "Invalid credentials")

# Voter Registration
@app.route('/register_voter', methods=['POST'])
@admin_required
def register_voter():
    """Register a new voter. Ensure age and CNIC validation before adding to the database."""
    data = request.json
    name = data.get('name')
    cnic = data.get('cnic')
    dob = data.get('dob')
    age = data.get('age')

    if mongo.db.voters.find_one({"cnic": cnic}):
        return format_response(False, "Voter already registered.")
    if int(age) < 18:
        return format_response(False, "Voter must be at least 18 years old.")
    mongo.db.voters.insert_one({
        "name": name, 
        "cnic": cnic, 
        "dob": dob, 
        "age": age, 
        "voted": False
    })
    return format_response(True, "Voter registered successfully.")

# Candidate Management
@app.route('/add_candidate', methods=['POST'])
@admin_required
def add_candidate():
    """Add a new candidate to the election. Prevent duplicate candidates."""
    data = request.json
    name = data.get('name')
    party = data.get('party')

    if mongo.db.candidates.find_one({"name": name, "party": party}):
        return format_response(False, "Candidate already exists.")
    mongo.db.candidates.insert_one({"name": name, "party": party})
    return format_response(True, "Candidate added successfully.")

# Election Scheduling
@app.route('/create_election', methods=['POST'])
@admin_required
def create_election():
    """Schedule a new election. Ensure valid date ranges before inserting into the database."""
    data = request.json
    name = data.get('name')
    start_date = datetime.fromisoformat(data.get('start_date'))
    end_date = datetime.fromisoformat(data.get('end_date'))

    if start_date >= end_date:
        return format_response(False, "Invalid election schedule.")
    mongo.db.elections.insert_one({
        "name": name, 
        "start_date": start_date, 
        "end_date": end_date, 
        "votes": {}
    })
    return format_response(True, "Election created successfully.")

# Delete Election
@app.route('/delete_election/<election_id>', methods=['DELETE'])
@admin_required
def delete_election(election_id):
    """Delete an election by its ID if it exists in the database."""
    result = mongo.db.elections.delete_one({"_id": election_id})
    if result.deleted_count == 0:
        return format_response(False, "Election not found.")
    return format_response(True, "Election deleted successfully.")

# Results and Analytics
@app.route('/get_results/<election_id>', methods=['GET'])
@login_required
def get_results(election_id):
    """Retrieve results of a specific election and determine the winning candidate."""
    election = mongo.db.elections.find_one({"_id": election_id})
    if not election:
        return format_response(False, "Election not found.")
    votes = election.get('votes', {})
    if not votes:
        return format_response(False, "No votes cast yet.")
    winner_id = max(votes, key=votes.get)
    winner = mongo.db.candidates.find_one({"_id": winner_id})
    return format_response(True, "Results retrieved successfully.", {
        "results": votes,
        "winner": {
            "candidate_id": winner_id,
            "name": winner['name'],
            "votes": votes[winner_id]
        }
    })

# Available Elections
@app.route('/available_elections', methods=['GET'])
@login_required
def available_elections():
    """List elections that are currently available for voting based on date and time."""
    current_time = datetime.now()
    elections = mongo.db.elections.find({
        "start_date": {"$lte": current_time}, 
        "end_date": {"$gte": current_time}
    })
    election_list = [{
        "election_id": str(election["_id"]), 
        "name": election["name"]
    } for election in elections]
    return format_response(True, "Available elections retrieved successfully.", election_list)

# Home Route
@app.route('/')
@login_required
def home():
    """Render the home page of the Election Management System."""
    return render_template('index.html')

# Login Page
@app.route('/login_page')
def login_page():
    """Render the login page for user authentication."""
    return render_template('login.html')

# Send Notification
@app.route('/send_notification', methods=['POST'])
@admin_required
def send_notification():
    """Send notifications to users, typically used for updates or alerts."""
    data = request.json
    recipient_id = data.get('recipient_id')
    message = data.get('message')

    if not recipient_id or not message:
        return format_response(False, "Recipient ID and message are required.")
    # Save the notification to the database
    mongo.db.notifications.insert_one({
        "recipient_id": recipient_id,
        "message": message,
        "timestamp": datetime.now()
    })
    return format_response(True, "Notification sent successfully.")

# Get Notifications
@app.route('/get_notifications/<recipient_id>', methods=['GET'])
@login_required
def get_notifications(recipient_id):
    """Retrieve all notifications for a specific recipient."""
    notifications = list(mongo.db.notifications.find({"recipient_id": recipient_id}))
    notifications_list = [
        {
            "message": notification["message"],
            "timestamp": notification["timestamp"]
        }
        for notification in notifications
    ]
    return format_response(True, "Notifications retrieved successfully.", notifications_list)

# Cast Vote
@app.route('/cast_vote', methods=['POST'])
@login_required
def cast_vote():
    """Allow users to cast their votes in a specific election."""
    data = request.json
    voter_id = session['user']['id']
    election_id = data.get('election_id')
    candidate_id = data.get('candidate_id')

    if not mongo.db.elections.find_one({"_id": election_id}):
        return format_response(False, "Election not found.")
    election = mongo.db.elections.find_one({"_id": election_id})
    if datetime.now() < election['start_date'] or datetime.now() > election['end_date']:
        return format_response(False, "Voting is not allowed for this election period.")
    if mongo.db.votes.find_one({"voter_id": voter_id, "election_id": election_id}):
        return format_response(False, "You have already voted in this election.")
    mongo.db.votes.insert_one({
        "voter_id": voter_id, 
        "election_id": election_id, 
        "candidate_id": candidate_id
    })
    # Notify the voter about the successful vote
    mongo.db.notifications.insert_one({
        "recipient_id": voter_id,
        "message": f"Your vote in election {election_id} has been successfully cast.",
        "timestamp": datetime.now()
    })

    return format_response(True, "Vote cast successfully.")

if __name__ == '__main__':
    app.run(debug=True)
