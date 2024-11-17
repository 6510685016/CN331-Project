from django.urls import path, include
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from . import views

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path('auth/', views.auth, name='auth'),
    path('resetpass/', PasswordResetView.as_view(template_name='registration/password_reset_form_use.html'), name='password_reset'),
    path('resetpass/done', PasswordResetDoneView.as_view(template_name='registration/password_reset_done_use.html'), name='password_reset_done'),
    path('resetpass/changpass/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm_use.html'), name='password_reset_confirm'),
    path('resetpass/complete', PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete_use.html'), name='password_reset_complete')
]