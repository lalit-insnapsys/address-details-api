from django.urls import path
from . import views # Importing the views module from the current package


urlpatterns = [
    path('', views.get_districts_list, name='districts-data'), # URL pattern for the Districts view
    path('<int:district_code>/', views.get_streets_by_district_code, name='streets-data'), # URL pattern for the Streets view
]
