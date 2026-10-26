from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('search/', views.food_search_view, name='food_search'),
    path('food/<int:food_id>/', views.food_detail_view, name='food_detail'),
    path('food/custom/', views.create_custom_food, name='create_custom_food'),
    path('food/import/', views.import_online_food, name='import_online_food'),
    path('food/<int:food_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('food/<int:food_id>/add/', views.add_to_diary, name='add_to_diary'),
    
    path('diary/', views.food_diary_view, name='food_diary'),
    path('diary/<int:entry_id>/edit/', views.edit_diary_entry, name='edit_diary_entry'),
    path('diary/<int:entry_id>/delete/', views.delete_diary_entry, name='delete_diary_entry'),
    
    path('history/', views.history_view, name='history'),
    path('profile/', views.profile_view, name='profile'),
    
    # API for dynamic calculations
    path('api/calculate/<int:food_id>/', views.nutrition_calculator_api, name='api_calculate'),
]
