import json
from decimal import Decimal
from datetime import datetime, timedelta, date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Sum, Q
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import UserProfile, NutritionGoal, Food, FoodDiaryEntry, FavoriteFood
from .forms import (
    UserRegistrationForm, UserProfileForm, NutritionGoalForm,
    CustomFoodForm, AddToDiaryForm, EditDiaryEntryForm
)
from .services import search_usda_foods, search_open_food_facts


def register_view(request):
    if request.user.is_authenticated:
        return redirect('tracker:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            # Initialize UserProfile and NutritionGoal
            UserProfile.objects.create(user=user)
            NutritionGoal.objects.create(user=user)
            login(request, user)
            messages.success(request, f"Welcome to NutriPulse, {user.username}! Your fitness journey begins today.")
            return redirect('tracker:dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'tracker/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('tracker:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'tracker:dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'tracker/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been securely logged out.")
    return redirect('tracker:login')


@login_required
def dashboard_view(request):
    user = request.user
    # Get or create goal and profile
    goal, _ = NutritionGoal.objects.get_or_create(user=user)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # Date handling (defaults to today)
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    # Fetch entries for selected date
    entries = FoodDiaryEntry.objects.filter(user=user, date=selected_date).select_related('food')

    # Group by meal
    meals = {
        'breakfast': {'entries': [], 'cals': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0},
        'lunch': {'entries': [], 'cals': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0},
        'dinner': {'entries': [], 'cals': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0},
        'snack': {'entries': [], 'cals': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0},
    }

    total_cals = Decimal('0.0')
    total_protein = Decimal('0.0')
    total_carbs = Decimal('0.0')
    total_fat = Decimal('0.0')
    total_fiber = Decimal('0.0')
    total_sugar = Decimal('0.0')
    total_sodium = Decimal('0.0')

    for entry in entries:
        m = entry.meal_type
        if m in meals:
            meals[m]['entries'].append(entry)
            meals[m]['cals'] += float(entry.calories)
            meals[m]['protein'] += float(entry.protein)
            meals[m]['carbs'] += float(entry.carbs)
            meals[m]['fat'] += float(entry.fat)

        total_cals += entry.calories
        total_protein += entry.protein
        total_carbs += entry.carbs
        total_fat += entry.fat
        total_fiber += entry.fiber
        total_sugar += entry.sugar
        total_sodium += entry.sodium

    remaining_cals = float(goal.daily_calories) - float(total_cals)

    # Progress percentages
    cals_pct = min(100, round((float(total_cals) / goal.daily_calories * 100) if goal.daily_calories else 0, 1))
    protein_pct = min(100, round((float(total_protein) / float(goal.protein_grams) * 100) if goal.protein_grams else 0, 1))
    carbs_pct = min(100, round((float(total_carbs) / float(goal.carbs_grams) * 100) if goal.carbs_grams else 0, 1))
    fat_pct = min(100, round((float(total_fat) / float(goal.fat_grams) * 100) if goal.fat_grams else 0, 1))

    # Weekly 7-day history for Chart.js
    week_days = []
    week_cals = []
    week_goals = []
    today = timezone.now().date()
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_entries = FoodDiaryEntry.objects.filter(user=user, date=d)
        day_total = day_entries.aggregate(Sum('calories'))['calories__sum'] or Decimal('0.0')
        week_days.append(d.strftime('%a (%b %d)'))
        week_cals.append(float(day_total))
        week_goals.append(goal.daily_calories)

    # Macro distribution for Doughnut Chart
    macro_chart = {
        'protein': float(total_protein),
        'carbs': float(total_carbs),
        'fat': float(total_fat),
    }

    # Recent distinct foods consumed
    recent_entries = FoodDiaryEntry.objects.filter(user=user).select_related('food').order_by('-created_at')[:6]

    context = {
        'selected_date': selected_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'is_today': (selected_date == today),
        'goal': goal,
        'profile': profile,
        'meals': meals,
        'total_cals': round(float(total_cals), 1),
        'remaining_cals': round(remaining_cals, 1),
        'total_protein': round(float(total_protein), 1),
        'total_carbs': round(float(total_carbs), 1),
        'total_fat': round(float(total_fat), 1),
        'total_fiber': round(float(total_fiber), 1),
        'total_sugar': round(float(total_sugar), 1),
        'total_sodium': round(float(total_sodium), 1),
        'cals_pct': cals_pct,
        'protein_pct': protein_pct,
        'carbs_pct': carbs_pct,
        'fat_pct': fat_pct,
        'week_days_json': json.dumps(week_days),
        'week_cals_json': json.dumps(week_cals),
        'week_goals_json': json.dumps(week_goals),
        'macro_chart_json': json.dumps(macro_chart),
        'recent_entries': recent_entries,
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
def food_diary_view(request):
    user = request.user
    goal, _ = NutritionGoal.objects.get_or_create(user=user)

    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    entries = FoodDiaryEntry.objects.filter(user=user, date=selected_date).select_related('food')

    meals_data = {
        'breakfast': {'name': 'Breakfast', 'entries': [], 'calories': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0},
        'lunch': {'name': 'Lunch', 'entries': [], 'calories': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0},
        'dinner': {'name': 'Dinner', 'entries': [], 'calories': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0},
        'snack': {'name': 'Snacks', 'entries': [], 'calories': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0},
    }

    day_totals = {'calories': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0, 'fiber': 0.0, 'sodium': 0.0}

    for entry in entries:
        m = entry.meal_type
        if m in meals_data:
            meals_data[m]['entries'].append(entry)
            meals_data[m]['calories'] += float(entry.calories)
            meals_data[m]['protein'] += float(entry.protein)
            meals_data[m]['carbs'] += float(entry.carbs)
            meals_data[m]['fat'] += float(entry.fat)

        day_totals['calories'] += float(entry.calories)
        day_totals['protein'] += float(entry.protein)
        day_totals['carbs'] += float(entry.carbs)
        day_totals['fat'] += float(entry.fat)
        day_totals['fiber'] += float(entry.fiber)
        day_totals['sodium'] += float(entry.sodium)

    for k in day_totals:
        day_totals[k] = round(day_totals[k], 1)
    for m in meals_data:
        for k in ['calories', 'protein', 'carbs', 'fat']:
            meals_data[m][k] = round(meals_data[m][k], 1)

    # Favorite food IDs for quick indication
    fav_ids = set(FavoriteFood.objects.filter(user=user).values_list('food_id', flat=True))

    context = {
        'selected_date': selected_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'is_today': (selected_date == timezone.now().date()),
        'meals_data': meals_data,
        'day_totals': day_totals,
        'goal': goal,
        'remaining_cals': round(float(goal.daily_calories) - day_totals['calories'], 1),
        'fav_ids': fav_ids,
    }
    return render(request, 'tracker/food_diary.html', context)


@login_required
def food_search_view(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    meal_type = request.GET.get('meal_type', 'lunch')
    target_date = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    include_online = request.GET.get('online', '1') == '1'

    # Filter local database (Curated + User custom)
    db_query = Q(created_by__isnull=True) | Q(created_by=request.user)
    if query:
        db_query &= (Q(name__icontains=query) | Q(brand_or_source__icontains=query))
    if category and category != 'all':
        db_query &= Q(category=category)

    local_foods = Food.objects.filter(db_query).order_by('name')[:30]

    online_results = []
    # If query is typed and online search allowed, fetch USDA & OpenFoodFacts safely
    if query and len(query) >= 2 and include_online:
        usda_res = search_usda_foods(query, page_size=4)
        off_res = search_open_food_facts(query, page_size=4)
        online_results = usda_res + off_res

    # User favorite foods
    favorites = FavoriteFood.objects.filter(user=request.user).select_related('food')

    categories = Food.CATEGORY_CHOICES

    context = {
        'query': query,
        'selected_category': category,
        'meal_type': meal_type,
        'target_date': target_date,
        'local_foods': local_foods,
        'online_results': online_results,
        'favorites': favorites,
        'categories': categories,
    }
    return render(request, 'tracker/food_search.html', context)


@login_required
def food_detail_view(request, food_id):
    food = get_object_or_404(Food, id=food_id)
    # Check permission: if custom, must belong to user
    if food.created_by and food.created_by != request.user:
        messages.error(request, "Access denied to this food item.")
        return redirect('tracker:food_search')

    meal_type = request.GET.get('meal_type', 'lunch')
    target_date = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    quantity = float(request.GET.get('quantity', 100))

    calc = food.calculate_nutrition(quantity)
    is_favorite = FavoriteFood.objects.filter(user=request.user, food=food).exists()

    context = {
        'food': food,
        'meal_type': meal_type,
        'target_date': target_date,
        'quantity': quantity,
        'calc': calc,
        'is_favorite': is_favorite,
    }
    return render(request, 'tracker/food_detail.html', context)


@login_required
def import_online_food(request):
    """
    Import an external food from USDA or Open Food Facts into the local database
    and redirect directly to detail/add screen.
    """
    if request.method == 'POST':
        name = request.POST.get('name', 'External Food').strip()
        brand = request.POST.get('brand_or_source', '')
        source_type = request.POST.get('source_type', 'curated')
        external_id = request.POST.get('external_id', '')

        # Check if already imported
        food = None
        if external_id:
            food = Food.objects.filter(external_id=external_id).first()

        if not food:
            try:
                food = Food.objects.create(
                    name=name,
                    brand_or_source=brand,
                    category=request.POST.get('category', 'packaged_branded'),
                    source_type=source_type,
                    external_id=external_id,
                    serving_weight_grams=Decimal(str(request.POST.get('serving_weight_grams', '100'))),
                    calories_per_100g=Decimal(str(request.POST.get('calories_per_100g', '0'))),
                    protein_per_100g=Decimal(str(request.POST.get('protein_per_100g', '0'))),
                    carbs_per_100g=Decimal(str(request.POST.get('carbs_per_100g', '0'))),
                    fat_per_100g=Decimal(str(request.POST.get('fat_per_100g', '0'))),
                    fiber_per_100g=Decimal(str(request.POST.get('fiber_per_100g', '0'))),
                    sugar_per_100g=Decimal(str(request.POST.get('sugar_per_100g', '0'))),
                    sodium_per_100g=Decimal(str(request.POST.get('sodium_per_100g', '0'))),
                )
            except Exception as e:
                messages.error(request, f"Could not import food: {e}")
                return redirect('tracker:food_search')

        meal_type = request.POST.get('meal_type', 'lunch')
        target_date = request.POST.get('date', timezone.now().date().strftime('%Y-%m-%d'))
        return redirect(f"/food/{food.id}/?meal_type={meal_type}&date={target_date}")

    return redirect('tracker:food_search')


@login_required
def create_custom_food(request):
    if request.method == 'POST':
        form = CustomFoodForm(request.POST)
        if form.is_valid():
            food = form.save(commit=False)
            food.created_by = request.user
            food.source_type = 'custom'
            food.save()
            messages.success(request, f"Custom food '{food.name}' created successfully!")
            return redirect('tracker:food_detail', food_id=food.id)
    else:
        form = CustomFoodForm()
    return render(request, 'tracker/custom_food.html', {'form': form})


@login_required
@require_POST
def add_to_diary(request, food_id):
    food = get_object_or_404(Food, id=food_id)
    if food.created_by and food.created_by != request.user:
        messages.error(request, "Permission denied.")
        return redirect('tracker:food_search')

    meal_type = request.POST.get('meal_type', 'lunch')
    date_str = request.POST.get('date')
    qty_str = request.POST.get('quantity_in_grams', '100')

    try:
        qty = Decimal(qty_str)
        if qty <= Decimal('0') or qty > Decimal('5000'):
            raise ValueError()
    except Exception:
        messages.error(request, "Please enter a valid quantity between 1 and 5000 grams.")
        return redirect('tracker:food_detail', food_id=food.id)

    try:
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        entry_date = timezone.now().date()

    entry = FoodDiaryEntry.objects.create(
        user=request.user,
        food=food,
        meal_type=meal_type,
        date=entry_date,
        quantity_in_grams=qty
    )
    messages.success(request, f"Added {entry.quantity_in_grams}g of {food.name} to {entry.get_meal_type_display()}!")
    return redirect(f"/diary/?date={entry_date.strftime('%Y-%m-%d')}")


@login_required
def edit_diary_entry(request, entry_id):
    entry = get_object_or_404(FoodDiaryEntry, id=entry_id, user=request.user)

    if request.method == 'POST':
        form = EditDiaryEntryForm(request.POST, instance=entry)
        if form.is_valid():
            saved_entry = form.save()
            messages.success(request, f"Updated {saved_entry.food.name} entry.")
            return redirect(f"/diary/?date={saved_entry.date.strftime('%Y-%m-%d')}")
    else:
        form = EditDiaryEntryForm(instance=entry)

    return render(request, 'tracker/edit_entry.html', {'form': form, 'entry': entry})


@login_required
@require_POST
def delete_diary_entry(request, entry_id):
    entry = get_object_or_404(FoodDiaryEntry, id=entry_id, user=request.user)
    date_str = entry.date.strftime('%Y-%m-%d')
    food_name = entry.food.name
    entry.delete()
    messages.info(request, f"Removed {food_name} from your diary.")
    return redirect(f"/diary/?date={date_str}")


@login_required
@require_POST
def toggle_favorite(request, food_id):
    food = get_object_or_404(Food, id=food_id)
    fav = FavoriteFood.objects.filter(user=request.user, food=food).first()

    if fav:
        fav.delete()
        is_fav = False
        msg = f"Removed {food.name} from favorites."
    else:
        FavoriteFood.objects.create(user=request.user, food=food)
        is_fav = True
        msg = f"Added {food.name} to favorites!"

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({'status': 'ok', 'is_favorite': is_fav, 'message': msg})

    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'tracker:dashboard'))


@login_required
def nutrition_calculator_api(request, food_id):
    """
    API endpoint for dynamic real-time client-side calculation previews,
    backed completely by server-side verification.
    """
    food = get_object_or_404(Food, id=food_id)
    try:
        qty = float(request.GET.get('quantity', 100))
        if qty < 0 or qty > 5000:
            return HttpResponseBadRequest("Invalid quantity.")
    except (ValueError, TypeError):
        qty = 100.0

    calc = food.calculate_nutrition(qty)
    return JsonResponse(calc)


@login_required
def profile_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    goal, _ = NutritionGoal.objects.get_or_create(user=user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            profile_form = UserProfileForm(request.POST, instance=profile)
            goal_form = NutritionGoalForm(instance=goal)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Fitness profile updated successfully.")
                return redirect('tracker:profile')
        elif action == 'update_goals':
            goal_form = NutritionGoalForm(request.POST, instance=goal)
            profile_form = UserProfileForm(instance=profile)
            if goal_form.is_valid():
                goal_form.save()
                messages.success(request, "Daily nutrition targets updated!")
                return redirect('tracker:profile')
        elif action == 'auto_calculate_macros':
            # Auto-calculate BMR and TDEE based on Harris-Benedict formula
            weight = float(profile.current_weight_kg or 70)
            height = float(profile.height_cm or 170)
            # Estimate age 25 if birth date not set
            age = 25
            if profile.date_of_birth:
                age = (timezone.now().date() - profile.date_of_birth).days // 365

            if profile.gender == 'F':
                bmr = 655.1 + (9.563 * weight) + (1.850 * height) - (4.676 * age)
            else:
                bmr = 66.47 + (13.75 * weight) + (5.003 * height) - (6.755 * age)

            multipliers = {
                'sedentary': 1.2,
                'light': 1.375,
                'moderate': 1.55,
                'very': 1.725,
                'extra': 1.9,
            }
            tdee = bmr * multipliers.get(profile.activity_level, 1.55)

            if profile.goal_type == 'lose':
                target_cals = int(tdee - 500)
            elif profile.goal_type == 'gain':
                target_cals = int(tdee + 400)
            else:
                target_cals = int(tdee)

            target_cals = max(1200, target_cals)
            # 30% Protein, 40% Carbs, 30% Fat distribution
            goal.daily_calories = target_cals
            goal.protein_grams = Decimal(str(round((target_cals * 0.30) / 4.0, 1)))
            goal.carbs_grams = Decimal(str(round((target_cals * 0.40) / 4.0, 1)))
            goal.fat_grams = Decimal(str(round((target_cals * 0.30) / 9.0, 1)))
            goal.fiber_grams = Decimal('30.0')
            goal.save()
            messages.success(request, f"Computed optimal daily plan: {target_cals} kcal based on your physical metrics!")
            return redirect('tracker:profile')
    else:
        profile_form = UserProfileForm(instance=profile)
        goal_form = NutritionGoalForm(instance=goal)

    context = {
        'profile_form': profile_form,
        'goal_form': goal_form,
        'profile': profile,
        'goal': goal,
    }
    return render(request, 'tracker/profile.html', context)


@login_required
def history_view(request):
    """
    Weekly & monthly historical trend analysis
    """
    user = request.user
    today = timezone.now().date()
    days = int(request.GET.get('days', 14))
    if days not in [7, 14, 30]:
        days = 14

    dates = []
    cals_list = []
    protein_list = []
    carbs_list = []
    fat_list = []

    goal, _ = NutritionGoal.objects.get_or_create(user=user)

    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        dates.append(d.strftime('%b %d'))
        day_entries = FoodDiaryEntry.objects.filter(user=user, date=d)
        totals = day_entries.aggregate(
            cals=Sum('calories'),
            prot=Sum('protein'),
            carb=Sum('carbs'),
            fat=Sum('fat')
        )
        cals_list.append(float(totals['cals'] or 0.0))
        protein_list.append(float(totals['prot'] or 0.0))
        carbs_list.append(float(totals['carb'] or 0.0))
        fat_list.append(float(totals['fat'] or 0.0))

    context = {
        'days': days,
        'goal_calories': goal.daily_calories,
        'dates_json': json.dumps(dates),
        'cals_json': json.dumps(cals_list),
        'protein_json': json.dumps(protein_list),
        'carbs_json': json.dumps(carbs_list),
        'fat_json': json.dumps(fat_list),
    }
    return render(request, 'tracker/history.html', context)
