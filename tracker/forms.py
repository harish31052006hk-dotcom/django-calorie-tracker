from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, NutritionGoal, Food, FoodDiaryEntry

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create password (min 8 chars)'})
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', "Passwords do not match!")
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['gender', 'date_of_birth', 'height_cm', 'current_weight_kg', 'target_weight_kg', 'activity_level', 'goal_type']
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'current_weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'target_weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'activity_level': forms.Select(attrs={'class': 'form-select'}),
            'goal_type': forms.Select(attrs={'class': 'form-select'}),
        }


class NutritionGoalForm(forms.ModelForm):
    class Meta:
        model = NutritionGoal
        fields = ['daily_calories', 'protein_grams', 'carbs_grams', 'fat_grams', 'fiber_grams', 'sodium_mg', 'sugar_grams']
        widgets = {
            'daily_calories': forms.NumberInput(attrs={'class': 'form-control', 'min': '500', 'max': '10000'}),
            'protein_grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'carbs_grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'fat_grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'fiber_grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'sodium_mg': forms.NumberInput(attrs={'class': 'form-control', 'step': '10'}),
            'sugar_grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        }


class CustomFoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = [
            'name', 'brand_or_source', 'category', 'serving_description', 'serving_weight_grams',
            'calories_per_100g', 'protein_per_100g', 'carbs_per_100g', 'fat_per_100g',
            'fiber_per_100g', 'sugar_per_100g', 'sodium_per_100g'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Homemade Masala Dosa'}),
            'brand_or_source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mom\'s Kitchen or Brand'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'serving_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1 dosa (120g)'}),
            'serving_weight_grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'calories_per_100g': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'protein_per_100g': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'carbs_per_100g': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'fat_per_100g': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'fiber_per_100g': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'sugar_per_100g': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'sodium_per_100g': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
        }


class AddToDiaryForm(forms.ModelForm):
    class Meta:
        model = FoodDiaryEntry
        fields = ['meal_type', 'date', 'quantity_in_grams']
        widgets = {
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantity_in_grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '1'}),
        }

    def clean_quantity_in_grams(self):
        qty = self.cleaned_data.get('quantity_in_grams')
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        if qty > 5000:
            raise forms.ValidationError("Quantity cannot exceed 5000 grams.")
        return qty


class EditDiaryEntryForm(forms.ModelForm):
    class Meta:
        model = FoodDiaryEntry
        fields = ['meal_type', 'quantity_in_grams', 'date']
        widgets = {
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity_in_grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '1'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_quantity_in_grams(self):
        qty = self.cleaned_data.get('quantity_in_grams')
        if qty is None or qty <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        if qty > 5000:
            raise forms.ValidationError("Quantity cannot exceed 5000 grams.")
        return qty
