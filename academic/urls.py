from django.urls import path
from . import views

urlpatterns = [
    path('session/create/', views.create_session, name='create_session'),
    path('sessions/', views.session_list, name='session_list'),
    path('session/<int:pk>/', views.session_detail, name='session_detail'),
    path('session/<int:session_id>/qr/', views.generate_qr, name='generate_qr'),
    path('session/<int:session_id>/attendance/', views.session_attendance_list, name='session_attendance_list'),
    path('justifications/', views.teacher_justifications, name='teacher_justifications'),
    path('justifications/<int:justification_id>/review/', views.review_justification, name='review_justification'),
]