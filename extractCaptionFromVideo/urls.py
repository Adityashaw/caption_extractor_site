from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('uploadVideo', views.upload_video, name="uploadVideo"),
    path('searchSubtitles', views.search_subtitles, name='searchSubtitles')
]
