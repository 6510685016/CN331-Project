from django.urls import path
from mainapp import views

urlpatterns = [
    path('', views.about, name='about'),
    path('main', views.main, name='main'),
    path('about', views.about, name='about'),
    path('analysis', views.analysis, name='analysis')
] 
