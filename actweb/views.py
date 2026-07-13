from flask import Blueprint, render_template, request, session, redirect, redirect
import hashlib
import time
import requests
from math import radians, sin, cos, sqrt, atan2
import random


views = Blueprint("views", __name__)

API_KEY = "4c9545464a69be40710b7e6ab6c6f7ae"
API_SECRET = "2JuASht2ij"

HOTEL_SEARCH_URL = "https://api.test.hotelbeds.com/hotel-api/1.0/hotels"
HOTEL_CONTENT_URL = "https://api.test.hotelbeds.com/hotel-content-api/1.0/hotels"
DESTINATIONS_URL = "https://api.test.hotelbeds.com/hotel-content-api/1.0/locations/destinations"


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


def search_hotels(destination_code):
    print("!!!!!!")
    print(destination_code)
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

    response = requests.post(
        HOTEL_SEARCH_URL,
        json=body,
        headers=get_headers()
    )

    print(response.status_code)
    print(response.text)

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

    selected_cities = session.get("selected_cities", [])

    if not selected_cities:
        return render_template(
            "accommodationSelection.html",
            hotels=[]
        )

    all_hotels = []

    # Search hotels for every selected city
    for city in selected_cities:

        search_data = search_hotels(city["code"])

        hotels = search_data["hotels"]["hotels"]

        all_hotels.extend(hotels)

    # Remove duplicates
    unique_hotels = {}
    for hotel in all_hotels:
        unique_hotels[hotel["code"]] = hotel

    hotels = list(unique_hotels.values())

    hotel_codes = [hotel["code"] for hotel in hotels]

    content_hotels = get_hotels_content(hotel_codes)

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
        if not images:
            continue

        enriched_hotels.append({
            "code": str(code),
            "name": content.get("name", hotel.get("name")),
            "description": content.get("description", {}).get("content", ""),
            "city": content.get("city", {}).get("content", hotel.get("city", "")),
            "country": content.get("country", {}).get("description", {}).get("content", hotel.get("country", "Demo")),
            "latitude": content.get("latitude") or content.get("coordinates", {}).get("latitude"),
            "longitude": content.get("longitude") or content.get("coordinates", {}).get("longitude"),
            "images": images,
            "facilities": content.get("facilities", [])
        })

    return render_template(
        "accommodationSelection.html",
        hotels=enriched_hotels,
        error=None
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

WORLD_GRAPH = {
    "Spain": ["Portugal", "France", "Italy"],
    "Portugal": ["Spain"],
    "France": ["Spain", "Belgium", "Germany", "Switzerland", "Italy", "United Kingdom", "Netherlands"],
    "United Kingdom": ["France", "Ireland"],
    "Ireland": ["United Kingdom"],
    "Belgium": ["France", "Netherlands", "Germany"],
    "Netherlands": ["Belgium", "Germany"],
    "Germany": ["France", "Netherlands", "Belgium", "Switzerland", "Austria", "Czech Republic", "Poland"],
    "Switzerland": ["France", "Germany", "Italy", "Austria"],
    "Italy": ["France", "Switzerland", "Austria", "Slovenia"],
    "Greece": ["Italy", "Turkey"],
    "Turkey": ["Greece", "Italy"],
    "Denmark": ["Germany", "Sweden"],
    "Sweden": ["Denmark", "Norway", "Finland"],
    "Norway": ["Sweden"],
    "Finland": ["Sweden"],
    "Poland": ["Germany", "Czech Republic", "Slovakia"],
    "Czech Republic": ["Germany", "Poland", "Austria", "Slovakia"],
    "Slovakia": ["Poland", "Czech Republic", "Austria"],
    "Hungary": ["Austria", "Slovakia", "Croatia", "Romania"],
    "Romania": ["Hungary", "Bulgaria"],
    "Croatia": ["Slovenia", "Hungary", "Italy"],
    "Slovenia": ["Italy", "Austria", "Croatia"],
    "Morocco": ["Spain", "France"],
    "Tunisia": ["France", "Italy"],
    "Egypt": ["Italy", "Greece"],
    "United Arab Emirates": ["Qatar", "Saudi Arabia", "Turkey"],
    "Qatar": ["United Arab Emirates", "Saudi Arabia"],
    "Saudi Arabia": ["United Arab Emirates", "Qatar", "Jordan"],
    "Jordan": ["Saudi Arabia", "Egypt"],
    "Thailand": ["Malaysia", "Singapore", "Vietnam"],
    "Vietnam": ["Thailand", "Cambodia"],
    "Cambodia": ["Vietnam", "Thailand"],
    "Malaysia": ["Thailand", "Singapore", "Indonesia"],
    "Singapore": ["Malaysia"],
    "Indonesia": ["Malaysia"],
    "Japan": ["South Korea"],
    "South Korea": ["Japan", "China"],
    "China": ["South Korea", "Hong Kong"],
    "Hong Kong": ["China"],
    "United States": ["Canada", "Mexico"],
    "Canada": ["United States"],
    "Mexico": ["United States", "Cuba"],
    "Cuba": ["Mexico", "Dominican Republic"],
    "Dominican Republic": ["Cuba", "United States"],
    "Brazil": ["Argentina", "Chile", "Peru"],
    "Argentina": ["Brazil", "Chile"],
    "Chile": ["Argentina", "Peru"],
    "Peru": ["Chile", "Brazil"]
}


# ----------------------------
# HOTELBEDS COUNTRY CODE MAP
# ----------------------------
COUNTRY_CODE_TO_NAME = {
    "ES": "Spain",
    "PT": "Portugal",
    "FR": "France",
    "GB": "United Kingdom",
    "IE": "Ireland",
    "BE": "Belgium",
    "NL": "Netherlands",
    "DE": "Germany",
    "CH": "Switzerland",
    "AT": "Austria",
    "IT": "Italy",
    "GR": "Greece",
    "TR": "Turkey",
    "DK": "Denmark",
    "SE": "Sweden",
    "NO": "Norway",
    "FI": "Finland",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "SK": "Slovakia",
    "HU": "Hungary",
    "RO": "Romania",
    "HR": "Croatia",
    "SI": "Slovenia",
    "MA": "Morocco",
    "TN": "Tunisia",
    "EG": "Egypt",
    "AE": "United Arab Emirates",
    "QA": "Qatar",
    "SA": "Saudi Arabia",
    "JO": "Jordan",
    "TH": "Thailand",
    "VN": "Vietnam",
    "KH": "Cambodia",
    "MY": "Malaysia",
    "SG": "Singapore",
    "ID": "Indonesia",
    "JP": "Japan",
    "KR": "South Korea",
    "CN": "China",
    "HK": "Hong Kong",
    "US": "United States",
    "CA": "Canada",
    "MX": "Mexico",
    "CU": "Cuba",
    "DO": "Dominican Republic",
    "BR": "Brazil",
    "AR": "Argentina",
    "CL": "Chile",
    "PE": "Peru"
}

CITY_LIBRARY = {
"ES": [
    {
        "name": "Barcelona",
        "code": "BCN",
        "country": "Spain",
        "latitude": 41.3851,
        "longitude": 2.1734
    },
    {
        "name": "Madrid",
        "code": "MAD",
        "country": "Spain",
        "latitude": 40.4168,
        "longitude": -3.7038
    },
    {
        "name": "Palma de Mallorca",
        "code": "PMI",
        "country": "Spain",
        "latitude": 39.5696,
        "longitude": 2.6502
    },
],

"PT": [
    {
        "name": "Lisbon",
        "code": "LIS",
        "country": "Portugal",
        "latitude": 38.7223,
        "longitude": -9.1393
    },
    {
        "name": "Porto",
        "code": "OPO",
        "country": "Portugal",
        "latitude": 41.1579,
        "longitude": -8.6291
    },
],

"FR": [
    {
        "name": "Paris",
        "code": "PAR",
        "country": "France",
        "latitude": 48.8566,
        "longitude": 2.3522
    },
    {
        "name": "Nice",
        "code": "NCE",
        "country": "France",
        "latitude": 43.7102,
        "longitude": 7.2620
    },
    {
        "name": "Lyon",
        "code": "LYS",
        "country": "France",
        "latitude": 45.7640,
        "longitude": 4.8357
    },
],

"GB": [
    {
        "name": "London",
        "code": "LON",
        "country": "United Kingdom",
        "latitude": 51.5074,
        "longitude": -0.1278
    },
    {
        "name": "Edinburgh",
        "code": "EDI",
        "country": "United Kingdom",
        "latitude": 55.9533,
        "longitude": -3.1883
    },
],

"IE": [
    {
        "name": "Dublin",
        "code": "DUB",
        "country": "Ireland",
        "latitude": 53.3498,
        "longitude": -6.2603
    },
],

"BE": [
    {
        "name": "Brussels",
        "code": "BRU",
        "country": "Belgium",
        "latitude": 50.8503,
        "longitude": 4.3517
    },
],

"NL": [
    {
        "name": "Amsterdam",
        "code": "AMS",
        "country": "Netherlands",
        "latitude": 52.3676,
        "longitude": 4.9041
    },
],

"DE": [
    {
        "name": "Berlin",
        "code": "BER",
        "country": "Germany",
        "latitude": 52.5200,
        "longitude": 13.4050
    },
    {
        "name": "Munich",
        "code": "MUC",
        "country": "Germany",
        "latitude": 48.1351,
        "longitude": 11.5820
    },
    {
        "name": "Frankfurt",
        "code": "FRA",
        "country": "Germany",
        "latitude": 50.1109,
        "longitude": 8.6821
    },
],
    "CH": [
    {
        "name": "Zurich",
        "code": "ZRH",
        "country": "Switzerland",
        "latitude": 47.3769,
        "longitude": 8.5417
    },
    {
        "name": "Geneva",
        "code": "GVA",
        "country": "Switzerland",
        "latitude": 46.2044,
        "longitude": 6.1432
    },
],

"AT": [
    {
        "name": "Vienna",
        "code": "VIE",
        "country": "Austria",
        "latitude": 48.2082,
        "longitude": 16.3738
    },
],

"IT": [
    {
        "name": "Rome",
        "code": "ROM",
        "country": "Italy",
        "latitude": 41.9028,
        "longitude": 12.4964
    },
    {
        "name": "Milan",
        "code": "MIL",
        "country": "Italy",
        "latitude": 45.4642,
        "longitude": 9.1900
    },
    {
        "name": "Venice",
        "code": "VCE",
        "country": "Italy",
        "latitude": 45.4408,
        "longitude": 12.3155
    },
],

"GR": [
    {
        "name": "Athens",
        "code": "ATH",
        "country": "Greece",
        "latitude": 37.9838,
        "longitude": 23.7275
    },
    {
        "name": "Santorini",
        "code": "JTR",
        "country": "Greece",
        "latitude": 36.3932,
        "longitude": 25.4615
    },
],

"TR": [
    {
        "name": "Istanbul",
        "code": "IST",
        "country": "Turkey",
        "latitude": 41.0082,
        "longitude": 28.9784
    },
    {
        "name": "Antalya",
        "code": "AYT",
        "country": "Turkey",
        "latitude": 36.8969,
        "longitude": 30.7133
    },
],

"DK": [
    {
        "name": "Copenhagen",
        "code": "CPH",
        "country": "Denmark",
        "latitude": 55.6761,
        "longitude": 12.5683
    },
],

"SE": [
    {
        "name": "Stockholm",
        "code": "STO",
        "country": "Sweden",
        "latitude": 59.3293,
        "longitude": 18.0686
    },
],

"NO": [
    {
        "name": "Oslo",
        "code": "OSL",
        "country": "Norway",
        "latitude": 59.9139,
        "longitude": 10.7522
    },
],

"FI": [
    {
        "name": "Helsinki",
        "code": "HEL",
        "country": "Finland",
        "latitude": 60.1699,
        "longitude": 24.9384
    },
],

"PL": [
    {
        "name": "Warsaw",
        "code": "WAW",
        "country": "Poland",
        "latitude": 52.2297,
        "longitude": 21.0122
    },
    {
        "name": "Krakow",
        "code": "KRK",
        "country": "Poland",
        "latitude": 50.0647,
        "longitude": 19.9450
    },
],

"CZ": [
    {
        "name": "Prague",
        "code": "PRG",
        "country": "Czech Republic",
        "latitude": 50.0755,
        "longitude": 14.4378
    },
],

"SK": [
    {
        "name": "Bratislava",
        "code": "BTS",
        "country": "Slovakia",
        "latitude": 48.1486,
        "longitude": 17.1077
    },
],

"HU": [
    {
        "name": "Budapest",
        "code": "BUD",
        "country": "Hungary",
        "latitude": 47.4979,
        "longitude": 19.0402
    },
],

"RO": [
    {
        "name": "Bucharest",
        "code": "BUH",
        "country": "Romania",
        "latitude": 44.4268,
        "longitude": 26.1025
    },
],

"HR": [
    {
        "name": "Dubrovnik",
        "code": "DBV",
        "country": "Croatia",
        "latitude": 42.6507,
        "longitude": 18.0944
    },
    {
        "name": "Split",
        "code": "SPU",
        "country": "Croatia",
        "latitude": 43.5081,
        "longitude": 16.4402
    },
],

"SI": [
    {
        "name": "Ljubljana",
        "code": "LJU",
        "country": "Slovenia",
        "latitude": 46.0569,
        "longitude": 14.5058
    },
],

"MA": [
    {
        "name": "Marrakech",
        "code": "RAK",
        "country": "Morocco",
        "latitude": 31.6295,
        "longitude": -7.9811
    },
    {
        "name": "Casablanca",
        "code": "CAS",
        "country": "Morocco",
        "latitude": 33.5731,
        "longitude": -7.5898
    },
],

"TN": [
    {
        "name": "Tunis",
        "code": "TUN",
        "country": "Tunisia",
        "latitude": 36.8065,
        "longitude": 10.1815
    },
],

"EG": [
    {
        "name": "Cairo",
        "code": "CAI",
        "country": "Egypt",
        "latitude": 30.0444,
        "longitude": 31.2357
    },
    {
        "name": "Hurghada",
        "code": "HRG",
        "country": "Egypt",
        "latitude": 27.2579,
        "longitude": 33.8116
    },
],
"AE": [
    {
        "name": "Dubai",
        "code": "DXB",
        "country": "United Arab Emirates",
        "latitude": 25.2048,
        "longitude": 55.2708
    },
    {
        "name": "Abu Dhabi",
        "code": "AUH",
        "country": "United Arab Emirates",
        "latitude": 24.4539,
        "longitude": 54.3773
    },
],

"QA": [
    {
        "name": "Doha",
        "code": "DOH",
        "country": "Qatar",
        "latitude": 25.2854,
        "longitude": 51.5310
    },
],

"SA": [
    {
        "name": "Riyadh",
        "code": "RUH",
        "country": "Saudi Arabia",
        "latitude": 24.7136,
        "longitude": 46.6753
    },
    {
        "name": "Jeddah",
        "code": "JED",
        "country": "Saudi Arabia",
        "latitude": 21.4858,
        "longitude": 39.1925
    },
],

"JO": [
    {
        "name": "Amman",
        "code": "AMM",
        "country": "Jordan",
        "latitude": 31.9539,
        "longitude": 35.9106
    },
],

"TH": [
    {
        "name": "Bangkok",
        "code": "BKK",
        "country": "Thailand",
        "latitude": 13.7563,
        "longitude": 100.5018
    },
    {
        "name": "Phuket",
        "code": "HKT",
        "country": "Thailand",
        "latitude": 7.8804,
        "longitude": 98.3923
    },
],

"VN": [
    {
        "name": "Ho Chi Minh City",
        "code": "SGN",
        "country": "Vietnam",
        "latitude": 10.8231,
        "longitude": 106.6297
    },
    {
        "name": "Hanoi",
        "code": "HAN",
        "country": "Vietnam",
        "latitude": 21.0278,
        "longitude": 105.8342
    },
],

"KH": [
    {
        "name": "Phnom Penh",
        "code": "PNH",
        "country": "Cambodia",
        "latitude": 11.5564,
        "longitude": 104.9282
    },
],

"MY": [
    {
        "name": "Kuala Lumpur",
        "code": "KUL",
        "country": "Malaysia",
        "latitude": 3.1390,
        "longitude": 101.6869
    },
],

"SG": [
    {
        "name": "Singapore",
        "code": "SIN",
        "country": "Singapore",
        "latitude": 1.3521,
        "longitude": 103.8198
    },
],

"ID": [
    {
        "name": "Bali",
        "code": "DPS",
        "country": "Indonesia",
        "latitude": -8.6500,
        "longitude": 115.2167
    },
    {
        "name": "Jakarta",
        "code": "JKT",
        "country": "Indonesia",
        "latitude": -6.2088,
        "longitude": 106.8456
    },
],

"JP": [
    {
        "name": "Tokyo",
        "code": "TYO",
        "country": "Japan",
        "latitude": 35.6762,
        "longitude": 139.6503
    },
    {
        "name": "Osaka",
        "code": "OSA",
        "country": "Japan",
        "latitude": 34.6937,
        "longitude": 135.5023
    },
    {
        "name": "Kyoto",
        "code": "UKY",
        "country": "Japan",
        "latitude": 35.0116,
        "longitude": 135.7681
    },
],

"KR": [
    {
        "name": "Seoul",
        "code": "SEL",
        "country": "South Korea",
        "latitude": 37.5665,
        "longitude": 126.9780
    },
],

"CN": [
    {
        "name": "Beijing",
        "code": "BJS",
        "country": "China",
        "latitude": 39.9042,
        "longitude": 116.4074
    },
    {
        "name": "Shanghai",
        "code": "SHA",
        "country": "China",
        "latitude": 31.2304,
        "longitude": 121.4737
    },
],

"HK": [
    {
        "name": "Hong Kong",
        "code": "HKG",
        "country": "Hong Kong",
        "latitude": 22.3193,
        "longitude": 114.1694
    },
],

"US": [
    {
        "name": "New York",
        "code": "NYC",
        "country": "United States",
        "latitude": 40.7128,
        "longitude": -74.0060
    },
    {
        "name": "Los Angeles",
        "code": "LAX",
        "country": "United States",
        "latitude": 34.0522,
        "longitude": -118.2437
    },
    {
        "name": "Miami",
        "code": "MIA",
        "country": "United States",
        "latitude": 25.7617,
        "longitude": -80.1918
    },
],

"CA": [
    {
        "name": "Toronto",
        "code": "YTO",
        "country": "Canada",
        "latitude": 43.6532,
        "longitude": -79.3832
    },
    {
        "name": "Vancouver",
        "code": "YVR",
        "country": "Canada",
        "latitude": 49.2827,
        "longitude": -123.1207
    },
],

"MX": [
    {
        "name": "Cancun",
        "code": "CUN",
        "country": "Mexico",
        "latitude": 21.1619,
        "longitude": -86.8515
    },
    {
        "name": "Mexico City",
        "code": "MEX",
        "country": "Mexico",
        "latitude": 19.4326,
        "longitude": -99.1332
    },
],

"CU": [
    {
        "name": "Havana",
        "code": "HAV",
        "country": "Cuba",
        "latitude": 23.1136,
        "longitude": -82.3666
    },
],

"DO": [
    {
        "name": "Punta Cana",
        "code": "PUJ",
        "country": "Dominican Republic",
        "latitude": 18.5601,
        "longitude": -68.3725
    },
],

"BR": [
    {
        "name": "Rio de Janeiro",
        "code": "RIO",
        "country": "Brazil",
        "latitude": -22.9068,
        "longitude": -43.1729
    },
    {
        "name": "São Paulo",
        "code": "SAO",
        "country": "Brazil",
        "latitude": -23.5505,
        "longitude": -46.6333
    },
],

"AR": [
    {
        "name": "Buenos Aires",
        "code": "BUE",
        "country": "Argentina",
        "latitude": -34.6037,
        "longitude": -58.3816
    },
],

"CL": [
    {
        "name": "Santiago",
        "code": "SCL",
        "country": "Chile",
        "latitude": -33.4489,
        "longitude": -70.6693
    },
],

"PE": [
    {
        "name": "Lima",
        "code": "LIM",
        "country": "Peru",
        "latitude": -12.0464,
        "longitude": -77.0428
    },
    {
        "name": "Cusco",
        "code": "CUZ",
        "country": "Peru",
        "latitude": -13.5319,
        "longitude": -71.9675
    },
]
}

@views.route("/citySelection")
def citySelection():

    selected_countries = session.get("selected_countries", [])

    country_name_to_code = {v: k for k, v in COUNTRY_CODE_TO_NAME.items()}

    available_cities = {}

    for country in selected_countries:
        code = country_name_to_code.get(country)

        if code and code in CITY_LIBRARY:
            available_cities[country] = CITY_LIBRARY[code]

    return render_template(
        "citySelection.html",
        cities=available_cities
    )
    

@views.route("/saveCities", methods=["POST"])
def saveCities():

    selected_cities = request.json

    session["selected_cities"] = selected_cities

    print(selected_cities)

    routes = generate_routes(selected_cities)

    print("Routes")
    print(routes)
    session["generated_routes"] = routes

    print("Generated routes:", routes)

    return {"success": True}


@views.route("/mapSelection")
def mapSelection():
    return("map.html")



@views.route("/destinationSelection")
def destinationSelection():

    session.setdefault("selected_countries", [])
    session.setdefault("rejected_countries", [])

    return render_template(
        "destinationSelection.html",
        world_graph=WORLD_GRAPH
    )


# ----------------------------
# COUNTRY ACCEPT
# ----------------------------
@views.route("/acceptCountry", methods=["POST"])
def acceptCountry():

    data = request.json

    selected = session.get("selected_countries", [])

    if data["country"] not in selected:
        selected.append(data["country"])

    session["selected_countries"] = selected

    return {"success": True}


# ----------------------------
# COUNTRY REJECT
# ----------------------------
@views.route("/rejectCountry", methods=["POST"])
def rejectCountry():

    data = request.json

    rejected = session.get("rejected_countries", [])

    if data["country"] not in rejected:
        rejected.append(data["country"])

    session["rejected_countries"] = rejected

    return {"success": True}
def haversine(city1, city2):

    R = 6371

    lat1 = radians(float(city1["latitude"]))
    lon1 = radians(float(city1["longitude"]))

    lat2 = radians(float(city2["latitude"]))
    lon2 = radians(float(city2["longitude"]))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


# ----------------------------------------------------
# TOTAL ROUTE DISTANCE
# ----------------------------------------------------
def total_distance(route):

    total = 0

    for i in range(len(route) - 1):
        total += haversine(route[i], route[i + 1])

    return round(total, 1)


# ----------------------------------------------------
# NEAREST NEIGHBOUR ROUTE
# ----------------------------------------------------
def nearest_route(cities):

    if not cities:
        print("HERE")
        return []

    remaining = cities[:]

    start = random.choice(remaining)

    route = [start]

    remaining.remove(start)

    while remaining:

        current = route[-1]

        next_city = min(
            remaining,
            key=lambda city: haversine(current, city)
        )

        route.append(next_city)

        remaining.remove(next_city)

    return route


# ----------------------------------------------------
# COUNT COUNTRIES
# ----------------------------------------------------
def count_countries(route):

    return len(set(city["country"] for city in route))


# ----------------------------------------------------
# GENERATE 4 ROUTES
# ----------------------------------------------------
def generate_routes(selected_cities):

    # Ignore cities without coordinates
    cities = [
        city for city in selected_cities
        if city.get("latitude") is not None
        and city.get("longitude") is not None
    ]
    print("linlon")
    print(cities)

    if len(cities) < 2:
        return []

    routes = []

    # ==================================================
    # EASY
    # ==================================================

    easy = nearest_route(cities)

    easy = easy[:min(3, len(easy))]

    routes.append({

        "name": "Easy",

        "difficulty": 1,

        "distance": total_distance(easy),

        "countries": count_countries(easy),

        "cities": easy

    })


    # ==================================================
    # BALANCED
    # ==================================================

    balanced = nearest_route(cities)

    balanced = balanced[:min(5, len(balanced))]

    routes.append({

        "name": "Balanced",

        "difficulty": 2,

        "distance": total_distance(balanced),

        "countries": count_countries(balanced),

        "cities": balanced

    })


    # ==================================================
    # EXPLORER
    # ==================================================

    explorer = []

    visited = set()

    # Try to visit different countries first
    for city in cities:

        if city["country"] not in visited:

            explorer.append(city)

            visited.add(city["country"])

    # Then add remaining cities
    for city in cities:

        if city not in explorer:

            explorer.append(city)

    explorer = nearest_route(explorer)

    explorer = explorer[:min(7, len(explorer))]

    routes.append({

        "name": "Explorer",

        "difficulty": 3,

        "distance": total_distance(explorer),

        "countries": count_countries(explorer),

        "cities": explorer

    })


    # ==================================================
    # GRAND TOUR
    # ==================================================

    grand = nearest_route(cities)

    routes.append({

        "name": "Grand Tour",

        "difficulty": 4,

        "distance": total_distance(grand),

        "countries": count_countries(grand),

        "cities": grand

    })

    return routes

@views.route("/routeSelection")
def routeSelection():

    routes = session.get("generated_routes", [])
    print(routes)

    return render_template(
        "routeSelection.html",
        routes=routes
    )

@views.route("/selectRoute", methods=["POST"])
def selectRoute():

    route_index = int(request.form["route"])

    routes = session.get("generated_routes", [])

    if route_index < 0 or route_index >= len(routes):
        return "Invalid route", 400

    selected_route = routes[route_index]

    # Save the complete route
    session["selected_route"] = selected_route

    # Save only the cities belonging to this route
    session["selected_cities"] = selected_route["cities"]

    return redirect("/accommodationSelection")

@views.route("/transportSelection")
def transportSelection():
    return render_template("transportSelection.html")


@views.route("/")
def accommodationSelection():
    return render_template("homePage.html")