from django.urls import path
from apps.school.views.school_view import SchoolListCreateView

urlpatterns = [
    path("schools/", SchoolListCreateView.as_view(), name="school-list-create"),
]
