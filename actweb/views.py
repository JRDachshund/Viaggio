from flask import Blueprint, render_template, request, session
import hashlib
import time
import requests

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
            "code": destination_code
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
        {"name": "Barcelona", "code": "BCN"},
        {"name": "Madrid", "code": "MAD"},
        {"name": "Palma de Mallorca", "code": "PMI"},
    ],
    "PT": [
        {"name": "Lisbon", "code": "LIS"},
        {"name": "Porto", "code": "OPO"},
    ],
    "FR": [
        {"name": "Paris", "code": "PAR"},
        {"name": "Nice", "code": "NCE"},
        {"name": "Lyon", "code": "LYS"},
    ],
    "GB": [
        {"name": "London", "code": "LON"},
        {"name": "Edinburgh", "code": "EDI"},
    ],
    "IE": [
        {"name": "Dublin", "code": "DUB"},
    ],
    "BE": [
        {"name": "Brussels", "code": "BRU"},
    ],
    "NL": [
        {"name": "Amsterdam", "code": "AMS"},
    ],
    "DE": [
        {"name": "Berlin", "code": "BER"},
        {"name": "Munich", "code": "MUC"},
        {"name": "Frankfurt", "code": "FRA"},
    ],
    "CH": [
        {"name": "Zurich", "code": "ZRH"},
        {"name": "Geneva", "code": "GVA"},
    ],
    "AT": [
        {"name": "Vienna", "code": "VIE"},
    ],
    "IT": [
        {"name": "Rome", "code": "ROM"},
        {"name": "Milan", "code": "MIL"},
        {"name": "Venice", "code": "VCE"},
    ],
    "GR": [
        {"name": "Athens", "code": "ATH"},
        {"name": "Santorini", "code": "JTR"},
    ],
    "TR": [
        {"name": "Istanbul", "code": "IST"},
        {"name": "Antalya", "code": "AYT"},
    ],
    "DK": [
        {"name": "Copenhagen", "code": "CPH"},
    ],
    "SE": [
        {"name": "Stockholm", "code": "STO"},
    ],
    "NO": [
        {"name": "Oslo", "code": "OSL"},
    ],
    "FI": [
        {"name": "Helsinki", "code": "HEL"},
    ],
    "PL": [
        {"name": "Warsaw", "code": "WAW"},
        {"name": "Krakow", "code": "KRK"},
    ],
    "CZ": [
        {"name": "Prague", "code": "PRG"},
    ],
    "SK": [
        {"name": "Bratislava", "code": "BTS"},
    ],
    "HU": [
        {"name": "Budapest", "code": "BUD"},
    ],
    "RO": [
        {"name": "Bucharest", "code": "BUH"},
    ],
    "HR": [
        {"name": "Dubrovnik", "code": "DBV"},
        {"name": "Split", "code": "SPU"},
    ],
    "SI": [
        {"name": "Ljubljana", "code": "LJU"},
    ],
    "MA": [
        {"name": "Marrakech", "code": "RAK"},
        {"name": "Casablanca", "code": "CAS"},
    ],
    "TN": [
        {"name": "Tunis", "code": "TUN"},
    ],
    "EG": [
        {"name": "Cairo", "code": "CAI"},
        {"name": "Hurghada", "code": "HRG"},
    ],
    "AE": [
        {"name": "Dubai", "code": "DXB"},
        {"name": "Abu Dhabi", "code": "AUH"},
    ],
    "QA": [
        {"name": "Doha", "code": "DOH"},
    ],
    "SA": [
        {"name": "Riyadh", "code": "RUH"},
        {"name": "Jeddah", "code": "JED"},
    ],
    "JO": [
        {"name": "Amman", "code": "AMM"},
    ],
    "TH": [
        {"name": "Bangkok", "code": "BKK"},
        {"name": "Phuket", "code": "HKT"},
    ],
    "VN": [
        {"name": "Ho Chi Minh City", "code": "SGN"},
        {"name": "Hanoi", "code": "HAN"},
    ],
    "KH": [
        {"name": "Phnom Penh", "code": "PNH"},
    ],
    "MY": [
        {"name": "Kuala Lumpur", "code": "KUL"},
    ],
    "SG": [
        {"name": "Singapore", "code": "SIN"},
    ],
    "ID": [
        {"name": "Bali", "code": "DPS"},
        {"name": "Jakarta", "code": "JKT"},
    ],
    "JP": [
        {"name": "Tokyo", "code": "TYO"},
        {"name": "Osaka", "code": "OSA"},
        {"name": "Kyoto", "code": "UKY"},
    ],
    "KR": [
        {"name": "Seoul", "code": "SEL"},
    ],
    "CN": [
        {"name": "Beijing", "code": "BJS"},
        {"name": "Shanghai", "code": "SHA"},
    ],
    "HK": [
        {"name": "Hong Kong", "code": "HKG"},
    ],
    "US": [
        {"name": "New York", "code": "NYC"},
        {"name": "Los Angeles", "code": "LAX"},
        {"name": "Miami", "code": "MIA"},
    ],
    "CA": [
        {"name": "Toronto", "code": "YTO"},
        {"name": "Vancouver", "code": "YVR"},
    ],
    "MX": [
        {"name": "Cancun", "code": "CUN"},
        {"name": "Mexico City", "code": "MEX"},
    ],
    "CU": [
        {"name": "Havana", "code": "HAV"},
    ],
    "DO": [
        {"name": "Punta Cana", "code": "PUJ"},
    ],
    "BR": [
        {"name": "Rio de Janeiro", "code": "RIO"},
        {"name": "São Paulo", "code": "SAO"},
    ],
    "AR": [
        {"name": "Buenos Aires", "code": "BUE"},
    ],
    "CL": [
        {"name": "Santiago", "code": "SCL"},
    ],
    "PE": [
        {"name": "Lima", "code": "LIM"},
        {"name": "Cusco", "code": "CUZ"},
    ],
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

    session["selected_cities"] = request.json

    return {"success": True}



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





@views.route("/transportSelection")
def transportSelection():
    return render_template("transportSelection.html")


@views.route("/")
def accommodationSelection():
    return render_template("homePage.html")