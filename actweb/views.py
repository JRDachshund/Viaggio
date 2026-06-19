from flask import Blueprint, render_template, request, session, Response, jsonify
import hashlib
import time
import requests

views = Blueprint("views", __name__)



API_KEY = "4c9545464a69be40710b7e6ab6c6f7ae"
API_SECRET = "2JuASht2ij"
HOTELBEDS_URL = "https://api.test.hotelbeds.com/hotel-api/1.0/hotels"

# Validate API
def get_headers():
    timestamp = str(int(time.time()))
    signature = hashlib.sha256((API_KEY + API_SECRET + timestamp).encode("utf-8")).hexdigest()

    return {
        "Api-key": API_KEY,
        "X-Signature": signature,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

# Get information via API
def search_hotels():

    body = {
        "stay": {
            "checkIn": "2026-07-10",
            "checkOut": "2026-07-15"
        },
        "occupancies": [
            {
                "rooms": 1,
                "adults": 2,
                "children": 0
            }
        ],
        "destination": {
            "code": "BCN"
        }
    }

    response = requests.post(
        HOTELBEDS_URL,
        json=body,
        headers=get_headers()
    )
    
    print("Status:", response.status_code)
    print("Response text:")
    #print(response.text)
    return response.json()

@views.route("/", methods=["GET", "POST"])
def home():

    data = search_hotels()

    hotels = data["hotels"]["hotels"]

    return render_template(
        "homePage.html",
        hotels=hotels
    )

@views.route("/map", methods=["GET", "POST"])
def map():
    return render_template('map.html')

@views.route("/destinationSelection", methods=["GET", "POST"])
def destinationSelection():
    return render_template('destinationSelection.html')

@views.route("/transportSelection", methods=["GET", "POST"])
def transportSelection():
    return render_template('transportSelection.html')

@views.route("/accommodationSelection", methods=["GET", "POST"])
def accommodationSelection():
    return render_template('accommodationSelection.html')

@views.route("/tripSummary", methods=["GET", "POST"])
# Hier sieht man die Übersicht über die geplante Reise und kann Unterkünfte buchen
def tripSummary(): 
    return render_template('tripSummary.html')

