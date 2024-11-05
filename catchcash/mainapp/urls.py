from django.urls import path
from mainapp import views

urlpatterns = [
    path('', views.about, name='about'),
    path('about', views.about, name='about'),
] 