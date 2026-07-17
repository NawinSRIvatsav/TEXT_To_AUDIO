from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('convert/', views.convert_view, name='convert'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('delete/<int:pk>/', views.delete_conversion, name='delete_conversion'),
    path('signup/', views.signup_view, name='signup'),
    path('', include('django.contrib.auth.urls')), # login/ and logout/
]
