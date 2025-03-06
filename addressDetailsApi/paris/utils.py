# Basic imports
import os
import requests
import json
import unicodedata
# Django imports
from django.conf import settings

# Utility imports
from urllib.parse import quote_plus

# Shapely imports
from shapely.geometry import shape, Point
# pyproj imports
from pyproj import Transformer

def remove_accents(text):
    """Removes accents from a given string."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def get_float_value(value: str) -> float:
    """
    Converts the given string value to a float.

    Args:
        value (str): The string value to convert.

    Returns:
        float: The converted float value or None if the conversion fails.
    """
    return float(value) if value else None
    

def fetch_permits_data(street_name: str, house_number: int):
    """
    Fetches planning permits from the PERMITS_DATA API.

    Args:
        cleaned_street_name (str): The formatted street name.
        house_number (int): The street number.

    Returns:
        dict: JSON response from the API or an error message.
    """
    BASE_DATA = os.getenv("PERMITS_DATA")
    try:
        permits_api_url = f"{BASE_DATA}&q={quote_plus(street_name)}&refine.numero_voirie_du_terrain={house_number}"
        response = requests.get(permits_api_url)
        response.raise_for_status()  # Raises an error for HTTP failures (e.g., 404, 500)
        return response.json()
    
    except requests.RequestException as e:
        return {"error": f"Failed to fetch permits: {str(e)}"}



def fetch_parcel_by_id(parcel_id: str):
    """
    Finds the parcel details and polygon using the given parcel ID.

    Args:
        parcel_id (str): The unique ID of the parcel.

    Returns:
        dict: Parcel details (if found) or an error message.
    """
    file_path = os.path.join(settings.BASE_DIR, "public", "cadastre-75-parcelles.json")

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            cadastre_data = json.load(file)
    except FileNotFoundError:
        return {"error": "Cadastral data not found."}

    # Search for the parcel with the matching ID
    for feature in cadastre_data["features"]:
        if feature.get("id") == parcel_id:
            return feature

    return {"error": f"No matching parcel found for ID {parcel_id}."}


def get_parcel_data(lat: float, lon: float):
    """
    Fetches parcel data using latitude and longitude, then finds the closest parcel ID.

    Args:
        lat (float): Latitude coordinate.
        lon (float): Longitude coordinate.

    Returns:
        dict: A dictionary containing:
            - "parcel_id": The closest parcel ID (or None if not found).
            - "parcel_data": The full response from the Reverse API.
    """
    BASE_URL = os.getenv("REVERSE_API_URL")
    try:
        reverse_api_url = f"{BASE_URL}&lat={lat}&lon={lon}"
        response = requests.get(reverse_api_url)
        response.raise_for_status()
        parcel_data = response.json()
    except requests.RequestException as e:
        return {"parcel_id": None, "parcel_data": {"error": f"Failed to fetch parcel data: {str(e)}"}}

    if not parcel_data or "features" not in parcel_data:
        return {"parcel_id": None, "parcel_data": parcel_data}

    # Find the closest parcel ID with minimum distance from the address point
    closest_distance = float("inf")
    parcel_id = None
    for feature in parcel_data["features"]:
        distance = feature.get("properties", {}).get("distance")
        if distance is not None and distance < closest_distance:
            closest_distance = distance
            parcel_id = feature["properties"].get("id")
    return {"parcel_id": parcel_id, "parcel_data": parcel_data}


def get_building_footprints(lat :float, lon :float):
    """
    Finds the building details and polygon using the given latitude and longitude.

    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.

    Returns:
        dict: Building details (if found) or an error message.
    """
    file_path = os.path.join(settings.BASE_DIR, "public", "cadastre-75-batiments.json")

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            building_data = json.load(file)
    except FileNotFoundError:
        return {"error": "Building data not found."}

    user_point = Point(lon, lat)
    point_buffered = user_point.buffer(0.00001)  # Tiny buffer around the point

    # Find the building that contains this point
    found_building = None
    for feature in building_data["features"]:
        geometry = shape(feature["geometry"])  # Convert GeoJSON geometry to Shapely shape

        # Use intersects() instead of contains()
        if geometry.intersects(user_point):
            found_building = feature
            break

        # If intersects() fails, try buffered point
        if geometry.intersects(point_buffered):
            found_building = feature
            break

    if found_building:
        return found_building
    else:
        return {"error": "No matching building found at this location."}

def convert_coordinates_into_lat_lon(x, y):
    """
    Converts coordinates from Lambert 93 (EPSG:2154) to WGS84 (EPSG:4326).
    
    Args:
        x (float): X coordinate in Lambert 93.
        y (float): Y coordinate in Lambert 93.

    Returns:
        tuple: (latitude, longitude) in WGS84.
    """

    transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)  # Reverse for Leaflet ([Lat, Lon])
    return lat, lon


def get_construction_year(attributes: dict) -> str:
    """
    Determines the construction year based on `an_const` (exact year) or `c_perconst` (construction period).
    
    Args:
        attributes (dict): Dictionary containing building attributes.

    Returns:
        str: Estimated construction year or period.
    """
    year = attributes.get("an_const")
    if year:
        return str(year)

    period_mapping = {
        1: "Before 1850",
        2: "from 1801 to 1850",
        3: "from 1851 to 1914",
        5: "from 1915 to 1939",
        6: "from 1940 to 1967",
        7: "from 1968 to 1975",
        8: "from 1976 to 1981",
        9: "from 1982 to 1989",
        10: "from 1990 to 1999",
        11: "2000 and up",
        12: "2008 and up",
        99: "Year Unknown"
    }
    
    return period_mapping.get(attributes.get("c_perconst"), "Year Unknown")


def get_cadastral_parcel_id(lat, lon):
    """
    Fetches all buildings in a given lat/lon region and extracts their n_sq_pc values.

    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.

    Returns: List of cadastral_parcel_id (n_sq_pc) values (same for the construction)
    """
    BASE_URL=os.getenv("FOOTPRINTS_DATA")
    params = settings.FOOTPRINTS_QUERY_PARAMS_FOR_CADASTRAL_PARCEL.copy()  # Parameters from config

    # Dynamically update the geometry parameter
    params["geometry"] = f"{lon-0.0001},{lat-0.0001},{lon+0.0001},{lat+0.0001}"

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if "features" not in data or len(data["features"]) == 0:
            return {"error": "No buildings found at this location."}

        # Extract unique n_sq_pc value
        cadastral_parcel_id_list = list(set(
            feature.get("attributes", {}).get("n_sq_pc") for feature in data["features"]
            if "attributes" in feature and feature["attributes"].get("n_sq_pc") is not None
        ))

        return cadastral_parcel_id_list  # Return the list of n_sq_pc value

    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    
    
def get_building_data_by_cadastral_parcel_id(cadastral_parcel_id_list):
    """
    Fetches full building data for the given list of cadastral_parcel_id (n_sq_pc) values, grouped by construction year.

    Args: 
        cadastral_parcel_id_list (int): Number of square meters per parcel/contract for a given building footprint. 
    
    Return: All the buildings footprints associated with the cadastral_parcel_id (n_sq_pc) value
    """
    BASE_URL = os.getenv("FOOTPRINTS_DATA")
    grouped_buildings = {}  # Store buildings by year

    for cadastral_parcel_id in cadastral_parcel_id_list:
        params = {
            "where": f"n_sq_pc = {cadastral_parcel_id}",  # Query filter by n_sq_pc
            "outFields": "*",  # Fetch all attributes
            "f": "json"
        }

        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if "features" not in data or len(data["features"]) == 0:
                continue  # Skip if no data for this cadastral_parcel_id

            for feature in data["features"]:
                attributes = feature.get("attributes", {})
                year = get_construction_year(attributes)

                # Convert coordinates if present
                if "geometry" in feature and "rings" in feature["geometry"]:
                    converted_rings = [
                        [convert_coordinates_into_lat_lon(x, y) for x, y in ring]
                        for ring in feature["geometry"]["rings"]
                    ]

                    feature["geometry"] = {
                        "type": "Polygon",
                        "coordinates": converted_rings
                    }

                # Add building to the correct year group
                if year not in grouped_buildings:
                    grouped_buildings[year] = []

                grouped_buildings[year].append({
                    "cadastral_parcel_id": attributes.get("n_sq_pc", "Not Available"),
                    "Shape_Area": attributes.get("Shape_Area", "Not Available"),
                    "Shape_Length": attributes.get("Shape_Length", "Not Available"),
                    "b_terrasse": attributes.get("b_terrasse", "Not Available"),
                    "geometry": feature["geometry"]
                })

        except requests.RequestException as e:
            print(f"API request failed for n_sq_pc {cadastral_parcel_id}: {str(e)}")
            continue

    return grouped_buildings  # Returning grouped data
