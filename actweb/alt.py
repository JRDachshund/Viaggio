# Import all modules
from flask import Blueprint, render_template, request, redirect
import hashlib
import time
import requests
from math import radians, sin, cos, sqrt, atan2
import random
from datetime import datetime
from city_country_information import WORLD_GRAPH, COUNTRY_CODE_TO_NAME, CITY_LIBRARY
from db_api import search_route


alt = Blueprint("alt", __name__)



# Hotelbeds API
API_KEY = "ba3fe51a820c56a77a89187aa213f12e"
API_SECRET = "sCPS5bvkdi"

HOTEL_SEARCH_URL = "https://api.test.hotelbeds.com/hotel-api/1.0/hotels"
HOTEL_CONTENT_URL = "https://api.test.hotelbeds.com/hotel-content-api/1.0/hotels"
DESTINATIONS_URL = "https://api.test.hotelbeds.com/hotel-content-api/1.0/locations/destinations"



# Variables in which all information that is selected (countries, cities, routes, transport, hotels) is stored.
# Cleared by going to the home page
# Could be done with seession storage but this proved more reliable for smallscale application
selected_countries = []

rejected_countries = []

selected_cities = []

generated_routes = []

selected_route = None

transport = []

selected_transport = []

selected_hotels = {}

rejected_hotels = []


# Clears all the selection/rejection global variables, called when accessing home
def reset_application_data():


    global selected_countries
    global rejected_countries
    global selected_cities
    global generated_routes
    global selected_route
    global transport
    global selected_transport
    global selected_hotels
    global rejected_hotels

    selected_countries.clear()
    rejected_countries.clear()
    selected_cities.clear()
    generated_routes.clear()

    selected_route = None

    transport.clear()
    selected_transport.clear()

    selected_hotels.clear()
    rejected_hotels.clear()

# Homepage
@alt.route("/")
def accommodationSelection():

    # clears all the selection/rejection global variables -> ensures you can plan a new trip
    reset_application_data()

    return render_template(
        "homePage.html"
    )

# country selection
# WORLD_GRAPH is imported from city_country_information.py and gives all the available countries
# and their neighbours to the html to display
@alt.route("/destinationSelection")
def destinationSelection():

    return render_template(

        "destinationSelection.html",

        world_graph=WORLD_GRAPH

    )

# accept country (this is called when user clicks "yes" on a country)
@alt.route("/acceptCountry", methods=["POST"])
def acceptCountry():

    # get accepted country's data
    data = request.json
    country = data["country"]

    # check to avoid doubles
    if country not in selected_countries:

        #save country in selected_countries
        selected_countries.append(country)

    # return success (function has to return something)
    return {"success": True}

# reject country (this is called when user clicks "no" on a country)
# this function serves to avoid reoffering rejected countries when reloading the page
@alt.route("/rejectCountry", methods=["POST"])
def rejectCountry():

    # get rejected country's data
    data = request.json
    country = data["country"]

    # check to avoid doubles
    if country not in rejected_countries:

        #save country in rejected_countries
        rejected_countries.append(country)

    # return success (function has to return something)
    return {"success": True}

@alt.route("/citySelection")
def citySelection():

    country_name_to_code = {
        value: key
        for key, value in COUNTRY_CODE_TO_NAME.items()
    }

    available_cities = []

    for country in selected_countries:

        code = country_name_to_code.get(country)

        if code and code in CITY_LIBRARY:
            available_cities.extend(CITY_LIBRARY[code])

    return render_template(
        "citySelection.html",
        cities=available_cities
    )


@alt.route("/saveCities", methods=["POST"])
def saveCities():

    global selected_cities

    incoming_cities = request.json

    # Replace the current list
    #selected_cities.clear()

    selected_cities.extend(
        incoming_cities
    )

    routes = generate_routes(
        selected_cities
    )

    generated_routes.clear()

    generated_routes.extend(routes)

    return {"success": True}


# generates headers for the hotelbeds API request
def get_headers():

    timestamp = str(int(time.time()))

    signature = hashlib.sha256(
        (
            API_KEY
            + API_SECRET
            + timestamp
        ).encode("utf-8")
    ).hexdigest()

    return {
        "Api-key": API_KEY,
        "X-Signature": signature,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def search_hotels(destination_code):

    # generates body for hotelbeds API request
    body = {
        "stay": {
            "checkIn": "2026-10-10",
            "checkOut": "2026-10-11"
        },
        "occupancies": [
            {
                "rooms": 1,
                "adults": 2,
                "children": 0
            }
        ],
        "destination": {
            "code": destination_code
        }
    }

    # sends request to the hotelbeds API and receives an answer
    # This particular URL only gives you availability info of certain hotels, not images, descriptions, etc.
    response = requests.post(
        HOTEL_SEARCH_URL,
        json=body,
        headers=get_headers()
    )

    # for debugging
    #print(response.status_code)
    #print(response.text)

    # get request status, especially relevant if an error occurs (e.g. 403)
    response.raise_for_status()

    # return the answer from hotelbeds
    return response.json()


def get_hotels_content(hotel_codes):

    hotels_dict = {}

    # We reduce the batch size to 50 as our API only allows us to make 50 requests at a time
    batch_size = 50

    # We loop through all the hotel codes in steps of 50 (batch_size)
    for i in range(0, len(hotel_codes), batch_size):

        # In one batch we include the partial list of all the codes from index i to i+batch_size
        # So in the first iteration this could be from 0 to 50
        batch = hotel_codes[i:i + batch_size]

        # We convert each hotel code in the batch to a String and then join them all together into a list (by comma)
        codes_string = ",".join(str(code) for code in batch)

        # These are the parameters we send hotelbeds
        params = {
            "codes": codes_string,
            "language": "ENG"
        }

        # We send the request and receive the answer
        response = requests.get(
            HOTEL_CONTENT_URL,
            headers=get_headers(),
            params=params
        )

        # Get the status of the request (e.g. 403), good to have in case of an error since it then stops the code
        response.raise_for_status()

        data = response.json()

        for hotel in data.get("hotels", []):
            hotels_dict[hotel["code"]] = hotel

    return hotels_dict


# Hotelbeds facility codes -> human-readable amenity labels (common set)
FACILITY_LABELS = {
    10: "Restaurant",
    20: "Bar",
    30: "Cafe",
    40: "24h reception",
    50: "Safe",
    55: "Elevator",
    60: "Currency exchange",
    70: "Shop",
    80: "Garden",
    90: "Terrace",
    95: "Wheelchair access",
    100: "Room service",
    120: "Laundry",
    130: "Medical service",
    135: "Bike hire",
    160: "Car park",
    170: "Garage",
    200: "WiFi",
    220: "Air conditioning",
    250: "Heating",
    260: "TV",
    270: "Hairdryer",
    280: "Minibar",
    287: "Fridge",
    295: "Kitchen",
    300: "Bath",
    310: "Shower",
    320: "Bathtub",
    330: "Jacuzzi",
    340: "Sauna",
    350: "Solarium",
    360: "Massage",
    365: "Spa",
    370: "Gym",
    390: "Pool",
    400: "Indoor pool",
    410: "Outdoor pool",
    420: "Children's pool",
    470: "Beach",
    490: "Tennis",
    500: "Golf",
    550: "Kids club",
    560: "Playground",
    575: "Babysitting",
    620: "Business centre",
    630: "Meeting rooms",
    640: "Banquet hall",
    670: "Concierge",
    730: "Pet friendly",
    740: "Non-smoking rooms",
    770: "Smoking rooms",
    850: "Airport shuttle",
    870: "Transfer service",
    895: "EV charging",
    995: "Electric kettle",
}


def hotelbeds_text(value, fallback=""):
    """Extract display text from Hotelbeds string or {content: ...} objects."""
    if value is None:
        return fallback
    if isinstance(value, dict):
        if value.get("content"):
            return str(value["content"])
        desc = value.get("description")
        if isinstance(desc, dict) and desc.get("content"):
            return str(desc["content"])
        if desc:
            return str(desc)
        return fallback
    text = str(value).strip()
    return text if text else fallback


def hotel_image_url(path):
    if not path:
        return ""
    path = str(path)
    if path.startswith("http"):
        return path
    return f"http://photos.hotelbeds.com/giata/{path}"


def normalize_hotel_images(images, limit=8):
    urls = []
    for image in images or []:
        path = image.get("path") if isinstance(image, dict) else None
        url = hotel_image_url(path)
        if url and url not in urls:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def extract_hotel_stars(content, search_hotel):
    """Best-effort star/category label from content or search payload."""
    for key in ("categoryName", "categoryCode"):
        label = hotelbeds_text(content.get(key) or search_hotel.get(key))
        if label:
            # e.g. "4EST" -> "4 stars" when it looks like a star code
            if label.endswith("EST") and label[0].isdigit():
                return f"{label[0]} stars"
            return label

    category = content.get("category") or search_hotel.get("category")
    if isinstance(category, dict):
        label = hotelbeds_text(category.get("description") or category.get("name") or category)
        if label:
            return label
        code = category.get("code")
        if code and str(code)[0:1].isdigit():
            return f"{str(code)[0]} stars"
    elif category:
        return str(category)

    for key in ("stars", "ranking", "S2C"):
        value = content.get(key) or search_hotel.get(key)
        if value is not None and value != "":
            try:
                n = int(float(value))
                if 1 <= n <= 5:
                    return f"{n} stars"
            except (TypeError, ValueError):
                return str(value)

    return None


def extract_hotel_price(search_hotel):
    """Lowest rate + currency from availability search, if present."""
    rate = search_hotel.get("minRate") or search_hotel.get("minRateFrom")
    if rate is None or rate == "":
        return None, None

    currency = search_hotel.get("currency") or "EUR"
    try:
        amount = float(rate)
        # Show whole euros when clean, otherwise one decimal
        if amount == int(amount):
            amount_str = str(int(amount))
        else:
            amount_str = f"{amount:.1f}"
    except (TypeError, ValueError):
        amount_str = str(rate)

    return amount_str, currency


def map_amenities(facilities, limit=6):
    labels = []
    seen = set()
    for facility in facilities or []:
        code = facility.get("facilityCode") if isinstance(facility, dict) else facility
        try:
            code = int(code)
        except (TypeError, ValueError):
            continue
        label = FACILITY_LABELS.get(code)
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
        if len(labels) >= limit:
            break
    return labels


def truncate_description(text, max_len=160):
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1].rsplit(" ", 1)[0]
    return (cut or text[: max_len - 1]) + "…"


# hotel selection
@alt.route("/accommodationSelection")
def home():

    #Fail-Safe if the list of selected cities is empty (e.g. if the user rejected every city)
    # In this case no hotels are available
    if not selected_cities:

        return render_template("accommodationSelection.html", hotels=[])


    all_hotels = []

    # Search hotels for every selected city
    for city in selected_cities:
        search_data = search_hotels(city["code"])
        hotels = search_data["hotels"]["hotels"]
        all_hotels.extend(hotels)

    # Remove duplicate hotels
    unique_hotels = {}

    for hotel in all_hotels:
        unique_hotels[hotel["code"]] = hotel

    hotels = list(unique_hotels.values())

    hotel_codes = [hotel["code"] for hotel in hotels]

    content_hotels = get_hotels_content(hotel_codes)

    selected_codes = []

    for city_hotels in selected_hotels.values():
        for hotel in city_hotels:
            selected_codes.append(str(hotel["code"]))

    enriched_hotels = []

    for hotel in hotels:

        code = hotel["code"]

        # Skip already selected hotels
        if str(code) in selected_codes:
            continue

        # Skip rejected hotels
        if str(code) in rejected_hotels:
            continue

        content = content_hotels.get(code, {})

        image_urls = normalize_hotel_images(content.get("images", []))

        if not image_urls:
            continue

        name = hotelbeds_text(content.get("name"), hotelbeds_text(hotel.get("name"), "Hotel"))
        description = hotelbeds_text(content.get("description"), "")
        city = hotelbeds_text(
            content.get("city"),
            hotelbeds_text(hotel.get("destinationName"), hotelbeds_text(hotel.get("city"), ""))
        )
        country = hotelbeds_text(content.get("country"), hotelbeds_text(hotel.get("country"), ""))

        min_rate, currency = extract_hotel_price(hotel)
        stars_label = extract_hotel_stars(content, hotel)
        amenities = map_amenities(content.get("facilities", []))

        coords = content.get("coordinates") or {}
        latitude = content.get("latitude") or coords.get("latitude") or hotel.get("latitude")
        longitude = content.get("longitude") or coords.get("longitude") or hotel.get("longitude")

        enriched_hotels.append({
            "code": str(code),
            "name": name,
            "description": description,
            "short_description": truncate_description(description),
            "city": city,
            "country": country,
            "latitude": latitude,
            "longitude": longitude,
            "images": image_urls,
            "image": image_urls[0],
            "min_rate": min_rate,
            "currency": currency,
            "stars_label": stars_label,
            "amenities": amenities,
        })

    return render_template("accommodationSelection.html", hotels=enriched_hotels, error=None)


@alt.route("/saveHotel", methods=["POST"])
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

    if city not in selected_hotels:
        selected_hotels[city] = []

    exists = False

    for hotel in selected_hotels[city]:
        if hotel["code"] == hotel_information["code"]:
            exists = True
            break

    if not exists:
        selected_hotels[city].append(hotel_information)

    return {"success": True}

# this is called when a hotel is rejected
# hotel info is saved so that you can reload the page without rejected hotels being displayed again
@alt.route("/rejectHotel", methods=["POST"])
def rejectHotel():

    # receives the data from the rejected hotel
    data = request.json

    # extracts the hotel code
    hotel_code = data["code"]

    # check whether hotel is already saved -> avoids doubles
    if hotel_code not in rejected_hotels:
        # adds to the rejected hotels list
        rejected_hotels.append(hotel_code)

    # return success (route has to return something)
    return {"success": True}


# Calculates the distance between two cities using the Haversine formula
# Distance is displayed when selecting the routes
def haversine(city1, city2):

    # radius of earth in km
    R = 6371

    # determine latitude and langitude of the cities 
    # convert these into floats so that mathematical operations can be performed
    # convert from degrees to radians as the trigonometry functions from the math module only accept radians
    lat1 = radians(float(city1["latitude"]))
    lon1 = radians(float(city1["longitude"]))

    lat2 = radians(float(city2["latitude"]))
    lon2 = radians(float(city2["longitude"]))

    # calculate the delta of lat and lon of the two cities
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # implementation of the Haversine formula
    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

# Calculates the total distance of a given route
def total_distance(route):

    # variable that stores the total distance
    total = 0

    # loops through the list of cities in the route and adds the distance betwwen the two cities to the total
    for i in range(len(route) - 1):
        total += haversine(route[i], route[i + 1])

    # return the total distance rounded to one decimal
    return round(total, 1)



def nearest_route(cities):

    if not cities:
        return []

    remaining = cities[:]

    start = random.choice(remaining)

    route = [start]

    remaining.remove(start)

    while remaining:
        current = route[-1]
        next_city = min(remaining, key=lambda city:haversine(current, city))

        route.append(next_city)
        remaining.remove(next_city)

    return route

# counts the amount of countries to be displayed in the route selection
def count_countries(route):
    # 
    return len(set(city["country"] for city in route))


def generate_routes(selected_cities):
    #print(selected_cities)
    cities = [city for city in selected_cities if city.get("latitude") is not None and city.get("longitude") is not None]
    
    if len(cities) < 2:
        return []

    routes = []


    # ========================================================
    # EASY
    # ========================================================

    easy = nearest_route(cities)

    easy = easy[:min(3, len(easy))]

    routes.append({

        "name": "Easy",

        "difficulty": 1,

        "distance": total_distance(
            easy
        ),

        "countries": count_countries(
            easy
        ),

        "cities": easy

    })


    # ========================================================
    # BALANCED
    # ========================================================

    balanced = nearest_route(cities)

    balanced = balanced[:min(4, len(balanced))]

    routes.append({

        "name": "Balanced",

        "difficulty": 2,

        "distance": total_distance(
            balanced
        ),

        "countries": count_countries(
            balanced
        ),

        "cities": balanced

    })


    # ========================================================
    # EXPLORER
    # ========================================================

    explorer = []

    visited = set()

    for city in cities:
        if city["country"] not in visited:
            explorer.append(city)
            visited.add(city["country"])

    for city in cities:
        if city not in explorer:
            explorer.append(city)

    explorer = nearest_route(explorer)

    explorer = explorer[:min(7, len(explorer))]

    routes.append({

        "name": "Explorer",

        "difficulty": 3,

        "distance": total_distance(
            explorer
        ),

        "countries": count_countries(
            explorer
        ),

        "cities": explorer

    })


    # ========================================================
    # GRAND TOUR
    # ========================================================

    grand = nearest_route(cities)

    routes.append({

        "name": "Grand Tour",

        "difficulty": 4,

        "distance": total_distance(
            grand
        ),

        "countries": count_countries(
            grand
        ),

        "cities": grand
    })


    return routes


# ============================================================
# ROUTE SELECTION
# ============================================================

@alt.route("/routeSelection")
def routeSelection():
    return render_template("routeSelection.html", routes=generated_routes)


# ============================================================
# TRANSPORT
# ============================================================

def build_transport(route):

    transport_options = []

    cities = route["cities"]

    for i in range(len(cities) - 1):

        from_city = cities[i]["name"]
        to_city = cities[i + 1]["name"]

        try:
            itinerary = search_route(cities[i], cities[i + 1])

            transport_options.append({

                "from": from_city,

                "to": to_city,

                "journey": itinerary

            })

        except Exception as e:

            transport_options.append({

                "from": from_city,

                "to": to_city,

                "journey": None,

                "error": str(e)

            })

    return transport_options


@alt.route("/selectRoute", methods=["POST"])
def selectRoute():

    global selected_route
    global transport

    route_index = int(
        request.form["route"]
    )

    if (route_index < 0 or route_index >= len(generated_routes)):
        return ("Invalid route", 400)


    selected_route = generated_routes[route_index]
    transport.clear()
    transport.extend(build_transport(selected_route))

    selected_route["transport"] = transport

    return redirect("/transportSelection")


@alt.route("/transportSelection")
def transportSelection():
    return render_template("transportSelection.html", transport=transport)


# ============================================================
# TRANSPORT CONFIRMATION
# ============================================================

@alt.route("/confirmTransport", methods=["POST"])
def confirmTransport():

    selected_transport.clear()

    for connection_index, connection in enumerate(transport):

        selected_index = request.form.get(f"transport_{connection_index}")

        if selected_index is None:
            return ("Please select a transport option for every route.", 400)

        selected_index = int(selected_index)

        journeys = connection.get("journey")

        if not journeys:
            return (f"No journey available for "f"{connection['from']} to "f"{connection['to']}.", 400)


        if (selected_index < 0 or selected_index >= len(journeys)):
            return ("Invalid journey selection.", 400)

        selected_journey = journeys[selected_index]

        selected_transport.append({

            "from": connection["from"],

            "to": connection["to"],

            "journey": selected_journey

        })


    return redirect("/accommodationSelection")

@alt.route("/map")
def map():

    # Variable for saving the entire transport options after being modified to be more easily displayed
    display_transport = []

    # loop through every journey
    for connection in selected_transport:


        journey = connection["journey"]


        # Raw journey structure:
        # journey[0] = duration in seconds
        # journey[1] = departure timestamp
        # journey[2] = arrival timestamp
        # journey[3] = transport mode
        # journey[4] = journey ID
        # journey[5:] = individual journey legs


        duration_seconds = journey[0]
        departure_timestamp = journey[1]
        arrival_timestamp = journey[2]
        mode = journey[3]
        legs = journey[5:]


        # Convert departure timestamp into display time
        departure_datetime = datetime.fromisoformat(departure_timestamp.replace("Z","+00:00"))
        departure_time = departure_datetime.strftime("%H:%M")

        # Convert arrival timestamp into display time
        arrival_datetime = datetime.fromisoformat(arrival_timestamp.replace("Z","+00:00"))
        arrival_time = arrival_datetime.strftime("%H:%M")

        # Convert duration from seconds to hours/minutes
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60

        if hours > 0:
            duration = (f"{hours}h "f"{minutes}m" )

        else:
            duration = (f"{minutes}m")

        # Add a display-ready connection


        display_transport.append({

            "from":
                connection["from"],

            "to":
                connection["to"],

            "departure_time":
                departure_time,

            "arrival_time":
                arrival_time,

            "duration":
                duration,

            "mode":
                mode,

            "legs":
                legs

        })

    return render_template("map.html", 
        selected_route=selected_route,
        selected_transport=display_transport,
        selected_hotels=selected_hotels
    )