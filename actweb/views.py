from flask import Blueprint, render_template, request, session
import hashlib
import time
import requests

views = Blueprint("views", __name__)

API_KEY = "4c9545464a69be40710b7e6ab6c6f7ae"
API_SECRET = "2JuASht2ij"

HOTEL_SEARCH_URL = "https://api.test.hotelbeds.com/hotel-api/1.0/hotels"
HOTEL_CONTENT_URL = "https://api.test.hotelbeds.com/hotel-content-api/1.0/hotels"


def get_headers():

    timestamp = str(int(time.time()))

    signature = hashlib.sha256(
        (API_KEY + API_SECRET + timestamp).encode("utf-8")
    ).hexdigest()

    return {
        "Api-key": API_KEY,
        "X-Signature": signature,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


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
        HOTEL_SEARCH_URL,
        json=body,
        headers=get_headers()
    )

    response.raise_for_status()

    return response.json()


def get_hotels_content(hotel_codes):

    hotels_dict = {}

    batch_size = 50

    for i in range(0, len(hotel_codes), batch_size):

        batch = hotel_codes[i:i + batch_size]

        codes_string = ",".join(str(code) for code in batch)

        params = {
            "codes": codes_string,
            "language": "ENG"
        }

        response = requests.get(
            HOTEL_CONTENT_URL,
            headers=get_headers(),
            params=params
        )

        response.raise_for_status()

        data = response.json()

        for hotel in data["hotels"]:
            hotels_dict[hotel["code"]] = hotel

    return hotels_dict


@views.route("/accommodationSelection")
def home():

    search_data = search_hotels()

    hotels = search_data["hotels"]["hotels"]

    hotel_codes = [hotel["code"] for hotel in hotels]

    content_hotels = get_hotels_content(hotel_codes)

    selected_hotels = session.get("selected_hotels", {})
    rejected_hotels = session.get("rejected_hotels", [])

    selected_codes = []

    for city_hotels in selected_hotels.values():
        for hotel in city_hotels:
            selected_codes.append(str(hotel["code"]))

    enriched_hotels = []

    for hotel in hotels:

        code = hotel["code"]

        if str(code) in selected_codes:
            continue

        if str(code) in rejected_hotels:
            continue

        content = content_hotels.get(code, {})

        images = content.get("images", [])

        if images:

            enriched_hotels.append({
                "code": str(code),
                "name": content.get("name", hotel.get("name")),
                "description": content.get("description", {}).get("content", ""),
                "city": content.get("city", {}).get("content"),
                "country": content.get("country", {}).get("description", {}).get("content"),
                "latitude": content.get("coordinates", {}).get("latitude"),
                "longitude": content.get("coordinates", {}).get("longitude"),
                "images": images,
                "facilities": content.get("facilities", [])
            })

    return render_template(
        "accommodationSelection.html",
        hotels=enriched_hotels
    )


@views.route("/saveHotel", methods=["POST"])
def saveHotel():

    data = request.json

    city = data["city"]

    hotel_information = {
        "code": data["code"],
        "name": data["name"],
        "description": data["description"],
        "country": data["country"],
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        "image": data["image"]
    }

    selected_hotels = session.get("selected_hotels", {})

    if city not in selected_hotels:
        selected_hotels[city] = []

    exists = False

    for hotel in selected_hotels[city]:
        if hotel["code"] == hotel_information["code"]:
            exists = True
            break

    if not exists:
        selected_hotels[city].append(hotel_information)

    session["selected_hotels"] = selected_hotels

    return {"success": True}


@views.route("/rejectHotel", methods=["POST"])
def rejectHotel():

    data = request.json

    rejected_hotels = session.get("rejected_hotels", [])

    if data["code"] not in rejected_hotels:
        rejected_hotels.append(data["code"])

    session["rejected_hotels"] = rejected_hotels

    return {"success": True}


@views.route("/tripSummary")
def tripSummary():

    selected_hotels = session.get("selected_hotels", {})

    return render_template(
        "tripSummary.html",
        selected_hotels=selected_hotels
    )


@views.route("/map")
def map():
    return render_template("map.html")


@views.route("/destinationSelection")
def destinationSelection():
    return render_template("destinationSelection.html")


@views.route("/transportSelection")
def transportSelection():
    return render_template("transportSelection.html")


@views.route("/")
def accommodationSelection():
    return render_template("homePage.html")