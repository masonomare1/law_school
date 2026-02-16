from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'api'

urlpatterns = [
    path('documents/', include('documents.urls')),
    path('query/', include('api.query_urls')),
]
