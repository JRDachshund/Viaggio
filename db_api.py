import requests
import json

BASE_URL = "https://api.transitous.org/api/v6/plan"


def search_route(origin, destination):
    """
    Search for the best public transport connection between two cities.

    origin and destination should be dictionaries containing:
        {
            "name": "...",
            "latitude": ...,
            "longitude": ...
        }
    """

    params = {
        "fromPlace": f"{origin['latitude']},{origin['longitude']}",
        "toPlace": f"{destination['latitude']},{destination['longitude']}",

        # Search all nearby stations
        "radius": 10000,

        # Transit only
        "transitModes": "TRANSIT",
        "directModes": "",

        # Search settings
        "numItineraries": 5,
        "maxTransfers": 5,
        "searchWindow": 7200,
        "detailedLegs": "true",
        "useRoutedTransfers": "true"
    }

    print("\n==============================")
    print(f"{origin['name']} -> {destination['name']}")
    print("==============================")
    print(params)

    headers = {
    "User-Agent": "MyTransitApp/1.0 (contact: your-email@example.com)"
}

    response = requests.get(
        BASE_URL,
        params=params,
        headers=headers
    )
    #response = requests.get(BASE_URL, params=params)

    print("\nStatus:", response.status_code)
    print("URL:", response.url)

    
    if response.status_code != 200:
        print("Response headers:")
        print(dict(response.headers))

        print("\nResponse body:")
        print(response.text)

        response.raise_for_status()

    data = response.json()

    #print("\nReturned keys:")
    #print(list(data.keys()))

    # Uncomment for debugging if needed
    # print(json.dumps(data, indent=2))

    # MOTIS may return either "itineraries" directly
    # or nested under "plan" depending on API version.
    itineraries = data.get("itineraries")

    if itineraries is None:
        itineraries = data.get("plan", {}).get("itineraries")

    if not itineraries:
        print("\nNo itineraries found.")

        if "direct" in data:
            print(f"Direct routes returned: {len(data['direct'])}")

        return None

    print(f"\nFound {len(itineraries)} itineraries.")
    #print(itineraries)

    routeOptions = []
   
    for i,j in enumerate(itineraries):

        first = itineraries[i]

        itineraryList = []

        print("\nReturned keys:")
        print(list(first.keys()))


        print("\nJourney summary:")

        duration = first.get("duration")
        startTime = first.get("startTime")
        endTime = first.get("endTime")
        transfers = first.get("transfers")
        id = first.get("id")
        itineraryList.extend([duration,startTime,endTime,transfers,id])

        for leg in first.get("legs", []):

            legList = []

            mode = leg.get("mode", "UNKNOWN")

            frm = leg.get("from", {}).get("name", "?")
            to = leg.get("to", {}).get("name", "?")
            legList.extend([mode,frm,to])
            itineraryList.append(legList)


            


            

            print(f"{mode}: {frm} -> {to}")
        routeOptions.append(itineraryList)

    print(routeOptions)

    

    return routeOptions