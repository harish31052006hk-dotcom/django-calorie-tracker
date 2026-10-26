// Real-time Nutrition Live Calculator preview
document.addEventListener('DOMContentLoaded', () => {
    const qtyInput = document.getElementById('calc-quantity-input');
    if (qtyInput) {
        const foodId = qtyInput.getAttribute('data-food-id');
        const calsDisplay = document.getElementById('preview-cals');
        const proteinDisplay = document.getElementById('preview-protein');
        const carbsDisplay = document.getElementById('preview-carbs');
        const fatDisplay = document.getElementById('preview-fat');
        const fiberDisplay = document.getElementById('preview-fiber');
        const sodiumDisplay = document.getElementById('preview-sodium');

        const updatePreview = () => {
            const qty = parseFloat(qtyInput.value) || 0;
            if (qty <= 0) return;

            // Fetch validated calculation from server API
            fetch(`/api/calculate/${foodId}/?quantity=${qty}`)
                .then(res => res.json())
                .then(data => {
                    if (calsDisplay) calsDisplay.textContent = data.calories + ' kcal';
                    if (proteinDisplay) proteinDisplay.textContent = data.protein + ' g';
                    if (carbsDisplay) carbsDisplay.textContent = data.carbs + ' g';
                    if (fatDisplay) fatDisplay.textContent = data.fat + ' g';
                    if (fiberDisplay) fiberDisplay.textContent = data.fiber + ' g';
                    if (sodiumDisplay) sodiumDisplay.textContent = data.sodium + ' mg';
                })
                .catch(err => console.error("Calc API error:", err));
        };

        qtyInput.addEventListener('input', updatePreview);
    }
});
