from django.urls import path
from . import views # Importing the views module from the current package


urlpatterns = [
    path('', views.get_districts_list, name='districts-data'), # URL pattern for the Districts view
    path('streets/<int:district_code>/', views.get_streets_by_district_code, name='streets-data'), # URL pattern for the Streets view
    path('addresses/<str:street_name>/', views.get_addresses_data, name='address-data'), # URL pattern for the Address-Search view
    path('history/<int:district_code>/<str:street_name>', views.get_street_history, name='streets-history'), # URL pattern for the Street-History view
    path('permits/<int:house_number>/<str:street_name>/<str:lat>/<str:lon>', views.get_planning_permits, name='planning-permits'), # URL pattern for the Address-Search view
]