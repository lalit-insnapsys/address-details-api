# standard library imports
import os
import requests
import re
import glob
import pandas as pd

# django imports
from rest_framework.decorators import api_view  # Importing api_view decorator from Django REST framework
from rest_framework.response import Response  # Importing Response to send HTTP responses
from rest_framework.request import Request  # Importing Request to send HTTP responses
from rest_framework import status

from urllib.parse import quote_plus

# local imports
from .utils import (
    get_float_value,        
    fetch_permits_data,   
    get_parcel_data,
    fetch_parcel_by_id,
    get_building_data_by_cadastral_parcel_id,
    get_cadastral_parcel_id,
    remove_accents,
)

@api_view(['GET'])
def get_districts_list(request: Request) -> Response:
    """
    Handles GET requests to fetch the list of districts from an external API.
    
    Args:
        request (Request): The HTTP request object.
    
    Returns:
        Response: A Response object containing the districts data or an error message.
    """
    BASE_URL: str = os.getenv("DISTRICTS_DATA_URL")  # Getting the base URL from environment variables

    try:
        response = requests.get(BASE_URL)  # Making a GET request to the external API
        response.raise_for_status()  # Raises an error for bad responses (4xx, 5xx)
        return Response(response.json(), status=status.HTTP_200_OK)  # Returning the data with a 200 OK status

    except requests.exceptions.RequestException as e:
        # Handling any request exceptions and returning a 500 Internal Server Error status
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_streets_by_district_code(request: Request, district_code: int) -> Response:
    """
    Fetches the list of streets based on district code.

    Args:
        district_code (int): The district code to filter streets.

    Returns:
        Response: A Response object containing the streets data by district code or an error message.
    """
    BASE_URL: str = os.getenv("STREETS_DATA_URL")  # Getting the base URL from environment variables
    # Determine the formatted arrondissement:
    # If district_code is a full postal code (>=75000), extract the last two digits.
    if district_code >= 75000:
        district_code = int(str(district_code)[-2:]) # Extract the last two digits
        formatted_district = f"{district_code:02d}e"
    else:
        formatted_district = f"{district_code:02d}e"
    query_params = {"refine.arrdt": formatted_district}  # Formatting district code properly

    try:
        response = requests.get(BASE_URL, params=query_params)
        response.raise_for_status()  # Raises an error for bad responses (4xx, 5xx)
        return Response(response.json(), status=status.HTTP_200_OK)

    except requests.exceptions.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_addresses_data(request: Request, street_name:str) -> Response:
    """
    Handles GET requests to fetch the list of addresses from an API.
    
    Args:
        street_name (str): Can be a street name or a street number followed by a street name.
    
    Returns:
        Response: A Response object containing the addresses data by street name or an error message.
    """
    BASE_URL: str = os.getenv("ADDRESS_DATA_URL")  # Getting the base URL from environment variables
    api_url = f"{BASE_URL}&q={street_name}"
    try:
        response = requests.get(api_url)  # Making a GET request to the external API
        response.raise_for_status()  # Raises an error for bad responses (4xx, 5xx)
        return Response(response.json(), status=status.HTTP_200_OK)  # Returning the data with a 200 OK status

    except requests.exceptions.RequestException as e:
        # Handling any request exceptions and returning a 500 Internal Server Error status
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def get_planning_permits(request, house_number: int, street_name: str, lat: str, lon: str) -> Response:
    """
    1.Fetches planning permits based on a street name, house number, and coordinates of the address.
    2.Then, finds the building footprint.

    Args:
        house_number (int): Street number, e.g., 111.
        street_name (str): Full address, e.g., "Rue du Château des Rentiers 75013 Paris".
        lat (str): Latitude of the location.
        lon (str): Longitude of the location.

    Returns:
        Response: JSON response with planning permits, parcel data, and the matched parcel polygon.
    """
    try:
        # Convert lat/lon to float
        lat_val = get_float_value(lat)
        lon_val = get_float_value(lon)

        if lat_val is None or lon_val is None:
            raise ValueError("Invalid latitude or longitude format.")

        # Fetch permits data
        permits_data = fetch_permits_data(street_name, house_number)

        # Get parcel data
        parcel_data = get_parcel_data(lat_val, lon_val)
        parcel_data = fetch_parcel_by_id(parcel_data.get("parcel_id"))

        # Step 1: Get the building footprint using latitude and longitude
        cadastral_parcel_id = get_cadastral_parcel_id(lat_val, lon_val)

        if not isinstance(cadastral_parcel_id, int):
            raise LookupError("No buildings found for this location.")

        # Step 2: Use n_sq_pc values to fetch complete building data
        grouped_building_data = get_building_data_by_cadastral_parcel_id(cadastral_parcel_id)
        
        
        return Response({
            "permits": permits_data,
            "parcel_data": parcel_data,
            "building_all_data": grouped_building_data
        }, status=status.HTTP_200_OK) 

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    except LookupError as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_street_history(request: Request, district_code: int, street_name: str) -> Response:
    """
    Fetches the history of a street in a given district.
    """
    try:
        STREETS_HISTORY = os.getenv("STREETS_HISTORY")
        
        # Convert full postal code (75013) → arrondissement number (13e)
        arrondissement_int = int(str(district_code)[-2:])  # Extract last 2 digits
        formatted_district = f"{arrondissement_int:02d}e"
        
        # Remove house number from `street_name`
        street_parts = street_name.split(" ")
        if street_parts[0].isdigit():  # If first part is a number (house number)
            street_name = " ".join(street_parts[1:])
        
        # Searching by typo field
        street_name=street_name.upper()
        street_name = remove_accents(street_name)
        encoded_query = quote_plus(f'typo="{street_name}"')

        refine_value = f'arrdt:"{formatted_district}"'
        encoded_refine_value = quote_plus(refine_value)

        api_url = f"{STREETS_HISTORY}&where={encoded_query}&refine={encoded_refine_value}"
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        records = response.json().get("results", [])
        if not records:
            return Response({"message": "No history found for this street."}, status=status.HTTP_404_NOT_FOUND)

        history = []
        for record in records:
            history.append({
                "district": formatted_district,
                "street_name": record.get("typo", "Unknown").title(),
                "historical_reference": record.get("historique", "No history available"),
                "opening_reference": record.get("ouverture", "No opening reference available"),
                "sanitation_reference": record.get("assainissement", "No sanitation reference available"),
                "original_reference": record.get("orig", "Unknown"),
            })

        return Response(history, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    except LookupError as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    
    except requests.exceptions.RequestException as e:
        return Response({"error": "Failed to fetch data from external API", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
