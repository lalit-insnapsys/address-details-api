from django.urls import path
from . import views # Importing the views module from the current package


urlpatterns = [
    path('', views.get_districts_list, name='paris-data'), # URL pattern for the Districts view
]
