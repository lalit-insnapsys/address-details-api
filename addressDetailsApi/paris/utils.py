# Description: Utility functions for the Paris Address Details API. 

# Basic imports
import os
import requests
import json

# Django imports
from django.conf import settings

# Utility imports
from urllib.parse import quote_plus

# Shapely imports
# from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.geometry import shape, Point, Polygon, MultiPolygon



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
            # return {
            #     "geometry": feature["geometry"],  # Polygon data
            #     "properties": feature["properties"]
            # }

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

    print("🛠️ Checking for point:", user_point)

    # Find the building that contains this point
    found_building = None
    for feature in building_data["features"]:
        geometry = shape(feature["geometry"])  # Convert GeoJSON geometry to Shapely shape

        # Use intersects() instead of contains()
        if geometry.intersects(user_point):
            print("✅ Found building via intersects():", feature["properties"])
            found_building = feature
            break

        # If intersects() fails, try buffered point
        if geometry.intersects(point_buffered):
            print("✅ Found building via buffer:", feature["properties"])
            found_building = feature
            break

    if found_building:
        return found_building
    else:
        return {"error": "No matching building found at this location."}
    # Search for the building containing the point
    # for feature in building_data.get("features", []):
    #     geometry = feature.get("geometry", {})
    #     coords = geometry.get("coordinates", [])

    #     try:
    #         if geometry["type"] == "MultiPolygon":
    #             building_shape = MultiPolygon([Polygon(poly[0]) for poly in coords])
    #         else:
    #             continue

    #         print(building_shape.contains(user_point))
    #         # Debugging: Check if our logic is working correctly
    #         if building_shape.contains(user_point):
    #             print(f"Building found: {feature['properties'].get('nom', 'Unknown')}")
    #             return {
    #                 "building_name": feature["properties"].get("nom", "Unknown"),
    #                 "commune": feature["properties"].get("commune", "Unknown"),
    #                 "created": feature["properties"].get("created", "Unknown"),
    #                 "updated": feature["properties"].get("updated", "Unknown"),
    #                 "geometry": feature["geometry"]
    #             }
    #     except Exception as e:
    #         print(f"Error processing feature: {e}")
    #         continue