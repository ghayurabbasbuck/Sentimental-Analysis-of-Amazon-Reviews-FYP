from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('reviews/scrape/', views.scrape_amazon_reviews, name='scrape_amazon_reviews'),
    path('perform_sentiment_analysis/', views.perform_sentiment_analysis, name='perform_sentiment_analysis'),
]
