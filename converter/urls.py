from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('convert/', views.convert_view, name='convert'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('delete/<int:pk>/', views.delete_conversion, name='delete_conversion'),
    path('signup/', views.signup_view, name='signup'),
    path('converter/translate-preview/', views.translate_preview, name='translate_preview'),
    path('converter/ocr-upload/', views.ocr_upload, name='ocr_upload'),
    path('converter/ocr-frame/', views.ocr_frame, name='ocr_frame'),
    path('converter/scan/', views.scan_webcam_view, name='scan_webcam'),
    path('image-generator/', views.image_generator_view, name='image_generator'),
    path('image-generator/delete/<int:pk>/', views.delete_image, name='delete_image'),
    path('', include('django.contrib.auth.urls')), # login/ and logout/
]
