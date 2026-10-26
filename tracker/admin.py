from django.contrib import admin
from .models import UserProfile, NutritionGoal, Food, FoodDiaryEntry, FavoriteFood, Recipe, RecipeIngredient

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'current_weight_kg', 'target_weight_kg', 'activity_level', 'goal_type')
    search_fields = ('user__username', 'user__email')

@admin.register(NutritionGoal)
class NutritionGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'daily_calories', 'protein_grams', 'carbs_grams', 'fat_grams')
    search_fields = ('user__username',)

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand_or_source', 'calories_per_100g', 'protein_per_100g', 'carbs_per_100g', 'fat_per_100g', 'source_type')
    list_filter = ('category', 'source_type')
    search_fields = ('name', 'brand_or_source')

@admin.register(FoodDiaryEntry)
class FoodDiaryEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'food', 'meal_type', 'date', 'quantity_in_grams', 'calories', 'protein')
    list_filter = ('meal_type', 'date')
    search_fields = ('user__username', 'food__name')

@admin.register(FavoriteFood)
class FavoriteFoodAdmin(admin.ModelAdmin):
    list_display = ('user', 'food', 'created_at')

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'servings', 'created_at')
