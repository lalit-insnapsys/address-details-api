# standard library imports
import os
import requests
import re
from urllib.parse import quote_plus

from django.http import JsonResponse  # Importing JsonResponse to send JSON responses

# django imports
from rest_framework.decorators import api_view  # Importing api_view decorator from Django REST framework
from rest_framework.response import Response  # Importing Response to send HTTP responses
from rest_framework.request import Request  # Importing Request to send HTTP responses
from rest_framework import status

@api_view(['GET'])
def get_districts_list(request: Request) -> Response:
    """
    Handles GET requests to fetch the list of districts from an external API.
    
    Args:
        request (Request): The HTTP request object.
    
    Returns:
        Response: A Response object containing the data or an error message.
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
        request (Request): The HTTP request object.
        district_code (int): The district code to filter streets.

    Returns:
        Response: A Response object containing the data or an error message.
    """
    BASE_URL: str = os.getenv("STREETS_DATA_URL")  # Getting the base URL from environment variables
    formatted_district = f"{district_code:02d}e"  # Ensure it's zero-padded (e.g., 1 -> 01e, 2 -> 02e)
    query_params = {"refine.arrdt": formatted_district}  # Formatting district code properly

    try:
        response = requests.get(BASE_URL, params=query_params)
        response.raise_for_status()  # Raises an error for bad responses (4xx, 5xx)
        return Response(response.json(), status=status.HTTP_200_OK)

    except requests.exceptions.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)