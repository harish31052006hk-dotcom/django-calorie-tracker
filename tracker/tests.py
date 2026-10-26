from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from tracker.models import Food, FoodDiaryEntry, NutritionGoal, UserProfile, FavoriteFood
from tracker.services import search_usda_foods, search_open_food_facts

class NutritionCalculationTests(TestCase):
    def setUp(self):
        self.food = Food.objects.create(
            name="Chicken Breast",
            category="meat_poultry",
            calories_per_100g=Decimal('165.0'),
            protein_per_100g=Decimal('31.0'),
            carbs_per_100g=Decimal('0.0'),
            fat_per_100g=Decimal('3.6'),
            fiber_per_100g=Decimal('0.0'),
            sodium_per_100g=Decimal('74.0')
        )

    def test_nutrition_formula_proportionality(self):
        """Formula: consumed_nutrient = nutrient_per_100g * quantity_in_grams / 100"""
        # Test for 200g (should exactly double values)
        calc200 = self.food.calculate_nutrition(200)
        self.assertEqual(calc200['calories'], 330.0)
        self.assertEqual(calc200['protein'], 62.0)
        self.assertEqual(calc200['fat'], 7.2)
        self.assertEqual(calc200['sodium'], 148.0)

        # Test for 50g (should halve values)
        calc50 = self.food.calculate_nutrition(50)
        self.assertEqual(calc50['calories'], 82.5)
        self.assertEqual(calc50['protein'], 15.5)
        self.assertEqual(calc50['fat'], 1.8)


class FoodDiaryCRUDAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='Password123!')
        self.user2 = User.objects.create_user(username='user2', password='Password123!')
        
        NutritionGoal.objects.create(user=self.user1, daily_calories=2200)
        NutritionGoal.objects.create(user=self.user2, daily_calories=1800)

        self.food = Food.objects.create(
            name="Idli",
            category="south_indian",
            calories_per_100g=Decimal('140.0'),
            protein_per_100g=Decimal('4.5'),
            carbs_per_100g=Decimal('28.0'),
            fat_per_100g=Decimal('0.5')
        )

    def test_food_diary_entry_creation_and_auto_calc(self):
        self.client.login(username='user1', password='Password123!')
        response = self.client.post(f"/food/{self.food.id}/add/", {
            'meal_type': 'breakfast',
            'date': '2026-10-26',
            'quantity_in_grams': '150'
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        entry = FoodDiaryEntry.objects.filter(user=self.user1).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.meal_type, 'breakfast')
        self.assertEqual(entry.quantity_in_grams, Decimal('150.00'))
        # 140 * 1.5 = 210.0 kcal
        self.assertEqual(entry.calories, Decimal('210.00'))
        # 4.5 * 1.5 = 6.75 -> 6.8 g
        self.assertEqual(entry.protein, Decimal('6.80'))

    def test_user_data_isolation(self):
        """Ensure User 2 cannot edit or delete User 1's diary entries"""
        entry1 = FoodDiaryEntry.objects.create(
            user=self.user1,
            food=self.food,
            meal_type='lunch',
            date=date.today(),
            quantity_in_grams=Decimal('100')
        )

        # Login as User 2 and attempt to delete User 1's entry
        self.client.login(username='user2', password='Password123!')
        response = self.client.post(f"/diary/{entry1.id}/delete/")
        # Should return 404 because query filters by user=request.user
        self.assertEqual(response.status_code, 404)

        # Verify entry still exists in DB
        self.assertTrue(FoodDiaryEntry.objects.filter(id=entry1.id).exists())

    def test_invalid_input_validation(self):
        self.client.login(username='user1', password='Password123!')
        # Negative quantity
        response = self.client.post(f"/food/{self.food.id}/add/", {
            'meal_type': 'breakfast',
            'date': '2026-10-26',
            'quantity_in_grams': '-50'
        }, follow=True)
        # Entry should not be added
        self.assertEqual(FoodDiaryEntry.objects.count(), 0)

        # Excessively huge quantity > 5000g
        response2 = self.client.post(f"/food/{self.food.id}/add/", {
            'meal_type': 'breakfast',
            'date': '2026-10-26',
            'quantity_in_grams': '999999'
        }, follow=True)
        self.assertEqual(FoodDiaryEntry.objects.count(), 0)

    def test_favorite_toggle(self):
        self.client.login(username='user1', password='Password123!')
        # Toggle on
        self.client.post(f"/food/{self.food.id}/favorite/")
        self.assertTrue(FavoriteFood.objects.filter(user=self.user1, food=self.food).exists())
        # Toggle off
        self.client.post(f"/food/{self.food.id}/favorite/")
        self.assertFalse(FavoriteFood.objects.filter(user=self.user1, food=self.food).exists())


class ExternalAPIGracefulHandlingTests(TestCase):
    def test_api_failure_fallback(self):
        """When an invalid or blank query is passed or network times out, service returns safe empty list"""
        res_usda = search_usda_foods("")
        self.assertEqual(res_usda, [])

        res_off = search_open_food_facts("x")
        self.assertEqual(res_off, [])
