from django.urls import path

from .views import GoogleOAuthView

urlpatterns = [path("google/auth", GoogleOAuthView.as_view())]
