from flask import Blueprint, render_template, request, session, redirect
import hashlib
import time
import requests
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
            hotels=[],
            error=None
        )

    if USE_FAKE_HOTEL_DATA:
        # Use reliable fake data instead of the rate-limited Hotelbeds test API
        all_hotels = []
        for city in selected_cities:
            all_hotels.extend(generate_fake_hotels(city))

        # Remove duplicates by code
        unique_hotels = {}
        for hotel in all_hotels:
            unique_hotels[hotel["code"]] = hotel
        hotels = list(unique_hotels.values())
    else:
        # Original real API path (kept for reference, currently disabled)
        hotel_search_cache = session.get("hotel_search_cache", {})
        all_hotels = []

        for city in selected_cities:
            city_code = city["code"]
            if city_code not in hotel_search_cache:
                try:
                    search_data = search_hotels(city_code)
                    hotel_search_cache[city_code] = search_data
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        return render_template(
                            "accommodationSelection.html",
                            hotels=[],
                            error="Rate limit reached from Hotelbeds test API (429 Too Many Requests). "
                                  "Please wait a minute or select fewer cities."
                        )
                    raise
            search_data = hotel_search_cache[city_code]
            all_hotels.extend(search_data["hotels"]["hotels"])

        session["hotel_search_cache"] = hotel_search_cache

        unique_hotels = {}
        for hotel in all_hotels:
            unique_hotels[hotel["code"]] = hotel
        hotels = list(unique_hotels.values())

    hotel_codes = [hotel["code"] for hotel in hotels]

    # For fake data we skip the expensive content API
    if USE_FAKE_HOTEL_DATA:
        content_hotels = {h["code"]: h for h in hotels}
    else:
        content_cache = session.get("content_cache", {})
        missing_codes = [code for code in hotel_codes if code not in content_cache]
        if missing_codes:
            try:
                new_content = get_hotels_content(missing_codes)
                content_cache.update(new_content)
                session["content_cache"] = content_cache
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    return render_template(
                        "accommodationSelection.html",
                        hotels=[],
                        error="Rate limit from Hotelbeds content API."
                    )
                raise
        content_hotels = content_cache

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

        if USE_FAKE_HOTEL_DATA:
            # Fake data is already in the final flat format
            images = hotel.get("images", [])
            if not images:
                continue
            enriched_hotels.append({
                "code": str(code),
                "name": hotel.get("name", ""),
                "description": hotel.get("description", ""),
                "city": hotel.get("city", ""),
                "country": hotel.get("country", "Demo"),
                "latitude": hotel.get("latitude"),
                "longitude": hotel.get("longitude"),
                "images": images,
                "facilities": hotel.get("facilities", [])
            })
        else:
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

# Switch to fake demo data for hotels (the real Hotelbeds test API has very strict rate limits)
USE_FAKE_HOTEL_DATA = True


def generate_fake_hotels(city):
    """Return fake but realistic hotel data for a given city."""
    city_name = city.get("name", "Demo City")
    random.seed(hash(city_name))  # same hotels every time for the same city

    templates = [
        {
            "name": f"Grand {city_name} Palace",
            "description": f"Luxury 5-star hotel in the heart of {city_name} with elegant rooms and excellent dining.",
            "facilities": [1, 2, 5, 12, 23, 45],
            "image_ids": [1015, 1016, 102, 103]
        },
        {
            "name": f"{city_name} Boutique Hotel",
            "description": f"Stylish boutique hotel with great service and a central location in {city_name}.",
            "facilities": [3, 8, 15, 30, 52],
            "image_ids": [104, 106, 107]
        },
        {
            "name": f"Sea View {city_name} Resort",
            "description": f"Beautiful resort with pool, spa and views near {city_name}. Perfect for relaxation.",
            "facilities": [1, 4, 9, 18, 25],
            "image_ids": [109, 110, 111]
        },
        {
            "name": f"Urban {city_name} Inn",
            "description": f"Modern, affordable hotel with free WiFi and comfortable rooms in {city_name}.",
            "facilities": [2, 6, 12, 20],
            "image_ids": [113, 114, 115]
        },
        {
            "name": f"Royal {city_name} Suites",
            "description": f"Exclusive luxury suites with premium service and amenities in the best part of {city_name}.",
            "facilities": [1, 5, 12, 23, 45, 67],
            "image_ids": [117, 118, 119]
        },
    ]

    hotels = []
    for i, t in enumerate(templates):
        code = 100000 + (abs(hash(city_name)) % 800000) + i
        lat = 30 + (abs(hash(city_name + str(i))) % 20)
        lon = -20 + (abs(hash(city_name + str(i))) % 40)

        images = [{"path": f"https://picsum.photos/id/{img_id}/400/300"} for img_id in t["image_ids"]]

        hotels.append({
            "code": str(code),
            "name": t["name"],
            "description": t["description"],
            "city": city_name,
            "country": "Demo Region",
            "latitude": round(lat + random.uniform(-0.3, 0.3), 4),
            "longitude": round(lon + random.uniform(-0.5, 0.5), 4),
            "images": images,
            "facilities": [{"facilityCode": f} for f in t["facilities"]],
        })

    return hotels[:4]


CITY_COORDS = {
    "BCN": [41.3851, 2.1734],
    "MAD": [40.4168, -3.7038],
    "PMI": [39.5696, 2.6502],
    "LIS": [38.7223, -9.1393],
    "OPO": [41.1496, -8.6110],
    "PAR": [48.8566, 2.3522],
    "NCE": [43.7102, 7.2620],
    "LYS": [45.7640, 4.8357],
    "LON": [51.5074, -0.1278],
    "EDI": [55.9533, -3.1883],
    "DUB": [53.3498, -6.2603],
    "BRU": [50.8503, 4.3517],
    "AMS": [52.3676, 4.9041],
    "BER": [52.5200, 13.4050],
    "MUC": [48.1351, 11.5820],
    "FRA": [50.1109, 8.6821],
    "ZRH": [47.3769, 8.5417],
    "GVA": [46.2044, 6.1432],
    "VIE": [48.2082, 16.3738],
    "ROM": [41.9028, 12.4964],
    "MIL": [45.4642, 9.1900],
    "VCE": [45.4408, 12.3155],
    "ATH": [37.9839, 23.7275],
    "JTR": [36.3932, 25.4615],
    "IST": [41.0082, 28.9784],
    "AYT": [36.8969, 30.7133],
    "CPH": [55.6761, 12.5683],
    "STO": [59.3293, 18.0686],
    "OSL": [59.9139, 10.7522],
    "HEL": [60.1699, 24.9384],
    "WAW": [52.2297, 21.0122],
    "KRK": [50.0647, 19.9450],
    "PRG": [50.0755, 14.4378],
    "BTS": [48.1459, 17.1077],
    "BUD": [47.4979, 19.0402],
    "BUH": [44.4268, 26.1025],
    "DBV": [42.6507, 18.0944],
    "SPU": [43.5081, 16.4402],
    "LJU": [46.0569, 14.5058],
    "RAK": [31.6295, -7.9811],
    "CAS": [33.5731, -7.5898],
    "TUN": [36.8065, 10.1815],
    "CAI": [30.0444, 31.2357],
    "HRG": [27.2579, 33.8116],
    "DXB": [25.2048, 55.2708],
    "AUH": [24.4539, 54.3773],
    "DOH": [25.2854, 51.5310],
    "RUH": [24.7136, 46.6753],
    "JED": [21.5433, 39.1728],
    "AMM": [31.9454, 35.9284],
    "BKK": [13.7563, 100.5018],
    "HKT": [7.8804, 98.3923],
    "SGN": [10.8231, 106.6297],
    "HAN": [21.0278, 105.8342],
    "PNH": [11.5564, 104.9282],
    "KUL": [3.1390, 101.6869],
    "SIN": [1.3521, 103.8198],
    "DPS": [-8.4095, 115.1889],
    "JKT": [-6.2088, 106.8456],
    "TYO": [35.6762, 139.6503],
    "OSA": [34.6937, 135.5023],
    "UKY": [35.0116, 135.7681],
    "SEL": [37.5665, 126.9780],
    "BJS": [39.9042, 116.4074],
    "SHA": [31.2304, 121.4737],
    "HKG": [22.3193, 114.1694],
    "NYC": [40.7128, -74.0060],
    "LAX": [34.0522, -118.2437],
    "MIA": [25.7617, -80.1918],
    "YTO": [43.6532, -79.3832],
    "YVR": [49.2827, -123.1207],
    "CUN": [21.1619, -86.8515],
    "MEX": [19.4326, -99.1332],
    "HAV": [23.1136, -82.3666],
    "PUJ": [18.5820, -68.4043],
    "RIO": [-22.9068, -43.1729],
    "SAO": [-23.5505, -46.6333],
    "BUE": [-34.6037, -58.3816],
    "SCL": [-33.4489, -70.6693],
    "LIM": [-12.0464, -77.0428],
    "CUZ": [-13.5319, -71.9675],
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


@views.route("/mapSelection")
def mapSelection():
    # Flatten all cities with coordinates
    all_cities = []
    code_to_country = {k: v for k, v in COUNTRY_CODE_TO_NAME.items()}

    for country_code, city_list in CITY_LIBRARY.items():
        country_name = code_to_country.get(country_code, country_code)
        for city in city_list:
            coords = CITY_COORDS.get(city["code"], [0.0, 0.0])
            all_cities.append({
                "name": city["name"],
                "code": city["code"],
                "country": country_name,
                "lat": coords[0],
                "lon": coords[1]
            })

    selected_cities = session.get("selected_cities", [])
    selected_codes = {c["code"] for c in selected_cities}

    return render_template(
        "mapSelection.html",
        cities=all_cities,
        selected_codes=list(selected_codes)
    )



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