
from django.contrib import admin
from django.urls import path
from search.views import dashboard

urlpatterns = [
    path('', dashboard, name='index'),
    
]
