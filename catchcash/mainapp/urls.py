from django.urls import path
from mainapp import views

urlpatterns = [
    path('', views.about, name='about'),
    path('main', views.main, name='main'),
    path('about', views.about, name='about'),
    path('analysis', views.analysis, name='analysis'),
    
    path('edit_statement/<int:id>/', views.edit_statement, name='edit_statement'),
    path('delete_statement/<int:id>/', views.delete_statement, name='delete_statement'),
    path('add_statement/', views.add_statement, name='add_statement'),
] 
