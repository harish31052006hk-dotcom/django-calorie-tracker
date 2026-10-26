import os
import requests
import logging

logger = logging.getLogger(__name__)

USDA_API_KEY = os.environ.get('USDA_API_KEY', 'DEMO_KEY')
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
OPEN_FOOD_FACTS_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

def search_usda_foods(query, page_size=8):
    """
    Search USDA FoodData Central backend API safely.
    Never exposes API keys to client.
    Handles timeouts and connection errors gracefully.
    """
    if not query or len(query.strip()) < 2:
        return []
    
    results = []
    try:
        params = {
            'api_key': USDA_API_KEY,
            'query': query,
            'pageSize': page_size,
            'dataType': 'Survey (FNDDS),Foundation Foods,SR Legacy',
        }
        resp = requests.get(USDA_SEARCH_URL, params=params, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get('foods', []):
                fdc_id = str(item.get('fdcId'))
                name = item.get('description', '').title()
                brand = item.get('brandOwner') or item.get('brandName') or 'USDA Standard Database'
                
                # Extract nutrients per 100g
                nutrients = {
                    'calories': 0.0,
                    'protein': 0.0,
                    'carbs': 0.0,
                    'fat': 0.0,
                    'fiber': 0.0,
                    'sugar': 0.0,
                    'sodium': 0.0,
                }
                for n in item.get('foodNutrients', []):
                    num = str(n.get('nutrientNumber', ''))
                    n_name = (n.get('nutrientName') or '').lower()
                    val = float(n.get('value', 0) or 0)
                    
                    if num == '208' or 'energy' in n_name:
                        # Ensure kcal
                        unit = (n.get('unitName') or '').lower()
                        if 'kj' in unit:
                            nutrients['calories'] = round(val / 4.184, 1)
                        else:
                            nutrients['calories'] = round(val, 1)
                    elif num == '203' or 'protein' in n_name:
                        nutrients['protein'] = round(val, 1)
                    elif num == '205' or 'carbohydrate' in n_name:
                        nutrients['carbs'] = round(val, 1)
                    elif num == '204' or 'total lipid' in n_name:
                        nutrients['fat'] = round(val, 1)
                    elif num == '291' or 'fiber' in n_name:
                        nutrients['fiber'] = round(val, 1)
                    elif num == '269' or 'sugars' in n_name:
                        nutrients['sugar'] = round(val, 1)
                    elif num == '307' or 'sodium' in n_name:
                        nutrients['sodium'] = round(val, 1)
                
                results.append({
                    'external_id': f"usda_{fdc_id}",
                    'name': name,
                    'brand_or_source': brand,
                    'category': 'international',
                    'source_type': 'usda',
                    'calories_per_100g': nutrients['calories'],
                    'protein_per_100g': nutrients['protein'],
                    'carbs_per_100g': nutrients['carbs'],
                    'fat_per_100g': nutrients['fat'],
                    'fiber_per_100g': nutrients['fiber'],
                    'sugar_per_100g': nutrients['sugar'],
                    'sodium_per_100g': nutrients['sodium'],
                    'serving_description': '100 g',
                    'serving_weight_grams': 100.0,
                })
    except Exception as e:
        logger.warning(f"USDA FoodData Central API call failed or timed out: {e}")
        # Soft fallback: local database will fulfill request
    return results


def search_open_food_facts(query, page_size=8):
    """
    Search Open Food Facts API backend.
    Public JSON API for packaged and international goods.
    """
    if not query or len(query.strip()) < 2:
        return []

    results = []
    try:
        headers = {
            'User-Agent': 'MyFitnessTracker-DjangoApp/1.0 (fitness-tracking@local.app)'
        }
        params = {
            'search_terms': query,
            'search_simple': 1,
            'action': 'process',
            'json': 1,
            'page_size': page_size,
        }
        resp = requests.get(OPEN_FOOD_FACTS_SEARCH_URL, params=params, headers=headers, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            for prod in data.get('products', []):
                p_code = prod.get('code') or prod.get('id')
                name = prod.get('product_name') or prod.get('generic_name')
                if not name:
                    continue
                brand = prod.get('brands') or 'Open Food Facts'
                nutriments = prod.get('nutriments', {})

                kcal = nutriments.get('energy-kcal_100g')
                if kcal is None:
                    energy_kj = nutriments.get('energy_100g')
                    kcal = (float(energy_kj) / 4.184) if energy_kj else 0.0

                results.append({
                    'external_id': f"off_{p_code}",
                    'name': name.strip().title(),
                    'brand_or_source': brand.strip(),
                    'category': 'packaged_branded',
                    'source_type': 'openfoodfacts',
                    'calories_per_100g': round(float(kcal or 0.0), 1),
                    'protein_per_100g': round(float(nutriments.get('proteins_100g', 0.0) or 0.0), 1),
                    'carbs_per_100g': round(float(nutriments.get('carbohydrates_100g', 0.0) or 0.0), 1),
                    'fat_per_100g': round(float(nutriments.get('fat_100g', 0.0) or 0.0), 1),
                    'fiber_per_100g': round(float(nutriments.get('fiber_100g', 0.0) or 0.0), 1),
                    'sugar_per_100g': round(float(nutriments.get('sugars_100g', 0.0) or 0.0), 1),
                    'sodium_per_100g': round(float((nutriments.get('sodium_100g', 0.0) or 0.0) * 1000), 1),
                    'serving_description': '100 g',
                    'serving_weight_grams': 100.0,
                })
    except Exception as e:
        logger.warning(f"Open Food Facts API call failed or timed out: {e}")
    return results
