from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    ACTIVITY_CHOICES = [
        ('sedentary', 'Sedentary (little or no exercise)'),
        ('light', 'Lightly active (light exercise 1-3 days/week)'),
        ('moderate', 'Moderately active (moderate exercise 3-5 days/week)'),
        ('very', 'Very active (hard exercise 6-7 days/week)'),
        ('extra', 'Extra active (very hard exercise & physical job)'),
    ]
    GOAL_TYPE_CHOICES = [
        ('maintain', 'Maintain Weight'),
        ('lose', 'Lose Weight (-0.5 kg/week)'),
        ('gain', 'Gain Weight (+0.5 kg/week)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, default=170.0)
    current_weight_kg = models.DecimalField(max_digits=5, decimal_places=1, default=70.0)
    target_weight_kg = models.DecimalField(max_digits=5, decimal_places=1, default=68.0)
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='moderate')
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES, default='maintain')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class NutritionGoal(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='nutrition_goal')
    daily_calories = models.PositiveIntegerField(default=2000, help_text="Daily calorie target (kcal)")
    protein_grams = models.DecimalField(max_digits=6, decimal_places=1, default=120.0, help_text="Target protein (g)")
    carbs_grams = models.DecimalField(max_digits=6, decimal_places=1, default=250.0, help_text="Target carbs (g)")
    fat_grams = models.DecimalField(max_digits=6, decimal_places=1, default=60.0, help_text="Target fat (g)")
    fiber_grams = models.DecimalField(max_digits=6, decimal_places=1, default=30.0, help_text="Target fiber (g)")
    sodium_mg = models.DecimalField(max_digits=6, decimal_places=1, default=2300.0, help_text="Sodium limit (mg)")
    sugar_grams = models.DecimalField(max_digits=6, decimal_places=1, default=50.0, help_text="Sugar limit (g)")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Goal ({self.daily_calories} kcal)"


class Food(models.Model):
    CATEGORY_CHOICES = [
        ('south_indian', 'South Indian'),
        ('north_indian', 'North Indian'),
        ('indian_general', 'Indian General / Street Food'),
        ('grains_cereals', 'Grains, Cereals & Oats'),
        ('meat_poultry', 'Poultry, Meat & Seafood'),
        ('dairy_eggs', 'Dairy & Eggs'),
        ('fruits_vegetables', 'Fruits & Vegetables'),
        ('snacks_bakery', 'Snacks & Bakery'),
        ('packaged_branded', 'Packaged & Branded Foods'),
        ('international', 'International / Other'),
    ]

    SOURCE_CHOICES = [
        ('custom', 'Custom User Food'),
        ('curated', 'Curated Database'),
        ('usda', 'USDA FoodData Central'),
        ('openfoodfacts', 'Open Food Facts'),
    ]

    name = models.CharField(max_length=255, db_index=True)
    brand_or_source = models.CharField(max_length=255, blank=True, default='')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='indian_general', db_index=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='curated')
    external_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_foods')

    # Nutritional values PER 100 GRAMS
    serving_unit = models.CharField(max_length=50, default='g', help_text="Default base is per 100g")
    serving_weight_grams = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('100.0'), help_text="Serving size in grams (100g standard)")
    serving_description = models.CharField(max_length=100, blank=True, default='100 g', help_text="e.g. 1 bowl (150g), 1 piece (40g)")

    calories_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.0'))
    protein_per_100g = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    carbs_per_100g = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    fat_per_100g = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    fiber_per_100g = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    sugar_per_100g = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    sodium_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.0'), help_text="in mg")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.calories_per_100g} kcal / 100g)"

    def calculate_nutrition(self, quantity_in_grams):
        """
        Formula: consumed_nutrient = nutrient_per_100g * quantity_in_grams / 100
        Server-side robust calculation using Decimal casting.
        """
        qty = Decimal(str(quantity_in_grams))
        factor = qty / Decimal('100.0')

        return {
            'quantity_g': round(float(qty), 2),
            'calories': round(float(Decimal(str(self.calories_per_100g or 0)) * factor), 1),
            'protein': round(float(Decimal(str(self.protein_per_100g or 0)) * factor), 1),
            'carbs': round(float(Decimal(str(self.carbs_per_100g or 0)) * factor), 1),
            'fat': round(float(Decimal(str(self.fat_per_100g or 0)) * factor), 1),
            'fiber': round(float(Decimal(str(self.fiber_per_100g or 0)) * factor), 1),
            'sugar': round(float(Decimal(str(self.sugar_per_100g or 0)) * factor), 1),
            'sodium': round(float(Decimal(str(self.sodium_per_100g or 0)) * factor), 1),
        }


class FoodDiaryEntry(models.Model):
    MEAL_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snacks'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='diary_entries')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='diary_entries')
    meal_type = models.CharField(max_length=20, choices=MEAL_CHOICES, db_index=True)
    date = models.DateField(default=timezone.now, db_index=True)
    quantity_in_grams = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('100.0'))

    # Persisted calculated values for accurate historical snapshots
    calories = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.0'))
    protein = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    carbs = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    fat = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    fiber = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    sugar = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    sodium = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.0'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'created_at']

    def save(self, *args, **kwargs):
        # Auto-compute calculated nutritional values based on quantity
        calc = self.food.calculate_nutrition(self.quantity_in_grams)
        self.calories = Decimal(str(calc['calories']))
        self.protein = Decimal(str(calc['protein']))
        self.carbs = Decimal(str(calc['carbs']))
        self.fat = Decimal(str(calc['fat']))
        self.fiber = Decimal(str(calc['fiber']))
        self.sugar = Decimal(str(calc['sugar']))
        self.sodium = Decimal(str(calc['sodium']))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.meal_type} - {self.food.name} ({self.quantity_in_grams}g)"


class FavoriteFood(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'food')

    def __str__(self):
        return f"{self.user.username}'s fav: {self.food.name}"


class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    servings = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by {self.user.username}"


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    quantity_in_grams = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('100.0'))

    def __str__(self):
        return f"{self.quantity_in_grams}g {self.food.name} in {self.recipe.name}"
