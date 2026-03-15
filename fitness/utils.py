from datetime import date
from decimal import Decimal

def calculate_age(birth_date):
    if not birth_date:
        return 30  # Default fallback
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def calculate_macros(profile):
    """
    Calculates Calories, Protein, Fats, and Carbs based on UserProfile.
    Uses Mifflin-St Jeor Equation.
    """
    height = float(profile.height or 175)
    weight = float(profile.current_weight or 70)
    age = calculate_age(profile.birth_date)
    gender = profile.gender or 'male'
    activity_level = profile.activity_level or 'light'
    goal = profile.goal or 'health'

    # 1. BMR Calculation
    if gender == 'male':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

    # 2. TDEE coefficients
    activity_map = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9,
    }
    tdee = bmr * activity_map.get(activity_level, 1.375)

    # 3. Goal Adjustment
    if goal == 'mass':
        target_calories = tdee + 300
        p_ratio, f_ratio = 2.0, 0.9  # g per kg
    elif goal == 'cut':
        target_calories = tdee - 500
        p_ratio, f_ratio = 2.2, 0.7
    else:  # health, strength, endurance, later
        target_calories = tdee
        p_ratio, f_ratio = 1.8, 0.8

    # 4. Macros in grams
    # Calories: P=4, C=4, F=9
    protein = weight * p_ratio
    fats = weight * f_ratio
    
    # Remaining calories for carbs
    consumed_cal = (protein * 4) + (fats * 9)
    carbs_cal = max(0, target_calories - consumed_cal)
    carbs = carbs_cal / 4

    return {
        'calories': int(target_calories),
        'protein': int(protein),
        'fats': int(fats),
        'carbs': int(carbs)
    }

def predict_weight_goal_date(weight_logs, target_weight):
    """
    Simple Linear Regression to predict when target weight will be reached.
    weight_logs: list of (date_obj, weight_decimal)
    returns: date_obj or None
    """
    if len(weight_logs) < 3:
        return None

    # Use days since first log as X
    first_date = weight_logs[0][0]
    x = [(log[0] - first_date).days for log in weight_logs]
    y = [float(log[1]) for log in weight_logs]

    n = len(x)
    if n == 0: return None
    
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(i*i for i in x)
    sum_xy = sum(i*j for i, j in zip(x, y))

    # Slope (m) and Intercept (b) for y = mx + b
    denominator = (n * sum_xx - sum_x**2)
    if denominator == 0:
        return None
        
    m = (n * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - m * sum_x) / n

    # Target weight = m * days + b  => days = (target - b) / m
    if m == 0:
        return None
        
    days_to_target = (float(target_weight) - b) / m
    
    if days_to_target <= 0:
        # Already reached or moving away from target
        return None
        
    # Cap at 2 years to avoid crazy numbers
    if days_to_target > 730:
        return None

    from datetime import timedelta
    predicted_date = first_date + timedelta(days=int(days_to_target))
    return predicted_date

def calculate_set_volume(sets_count, reps_str, weight_str, is_bodyweight=False):
    """
    Centralized volume calculation logic.
    Supports individual values and hyphen-separated sequences (e.g. '10-8-6').
    """
    if is_bodyweight:
        return 0.0
        
    # Parse reps
    reps_raw = str(reps_str).replace(',', '-').replace(' ', '-')
    reps_list = [int(r) for r in reps_raw.split('-') if r.isdigit()]
    
    # Parse weight
    w_raw = str(weight_str or '0').replace(',', '-').replace(' ', '-')
    w_list = [float(w) for w in w_raw.split('-') if w.replace('.', '', 1).isdigit()]
    
    if not reps_list or not w_list:
        return 0.0

    total_vol = 0.0
    
    if len(reps_list) == 1:
        # Single value for reps, multiply by number of sets
        total_vol = reps_list[0] * sets_count * w_list[0]
    else:
        # Multiple values for reps (e.g. 10-8-6)
        for i, r in enumerate(reps_list):
            # Use current weight from list or last available weight if list is shorter
            current_w = w_list[i] if i < len(w_list) else w_list[-1]
            total_vol += r * current_w
            
    return float(total_vol)

def calculate_streak(user):
    """
    Optimized streak calculation. 
    Fetches all workout dates once and calculates consecutive weeks in-memory.
    """
    # Import inside to avoid circular deps
    from .models import Workout
    from django.utils import timezone
    from datetime import timedelta
    
    # Fetch only dates, ordered descending
    workout_dates = list(Workout.objects.filter(user=user).values_list('date', flat=True).order_by('-date'))
    
    if not workout_dates:
        return 0
        
    today = timezone.now().date()
    # Start of current calendar week (Monday)
    week_start = today - timedelta(days=today.weekday())
    
    # Check if there is a workout this week or last week
    has_this_week = any(d >= week_start for d in workout_dates)
    has_last_week = any(week_start - timedelta(days=7) <= d < week_start for d in workout_dates)
    
    if not has_this_week and not has_last_week:
        return 0
        
    streak = 0
    curr_ws = week_start if has_this_week else (week_start - timedelta(days=7))
    
    while True:
        # Check if any workout falls into the current week window
        if any(curr_ws <= d <= curr_ws + timedelta(days=6) for d in workout_dates):
            streak += 1
            curr_ws -= timedelta(days=7)
        else:
            break
            
    return streak
