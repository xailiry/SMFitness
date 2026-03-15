import os
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from fitness.models import UserProfile, Workout, WorkoutSet, Exercise, CardioEntry, WeightLog

def create_test_data():
    username = 'test_athlete'
    password = 'password123'
    
    # Clean up existing test user
    User.objects.filter(username=username).delete()
    
    user = User.objects.create_user(username=username, password=password)
    profile = user.profile
    profile.gender = 'male'
    profile.height = 171
    profile.current_weight = 66.0
    profile.target_weight = 75.0
    profile.birth_date = datetime(1995, 5, 20).date()
    # Choose from choices: sedentary, light, moderate, very_active, extra_active
    profile.activity_level = 'moderate'
    # Choose from: mass, cut, strength, endurance, health
    profile.goal = 'mass'
    profile.save()
    
    # Ensure exercises exist
    bench_press, _ = Exercise.objects.get_or_create(
        name='Жим лежа',
        defaults={'muscle_group': 'chest', 'description': 'Базовое упражнение для груди'}
    )
    squat, _ = Exercise.objects.get_or_create(
        name='Приседания',
        defaults={'muscle_group': 'legs', 'description': 'Базовое упражнение для ног'}
    )
    
    end_date = datetime(2026, 3, 15).date()
    start_date = end_date - timedelta(days=120)
    
    base_weight = 66.0
    
    current_date = start_date
    workout_count = 0
    today_weight = base_weight
    
    print(f"Creating 4 months of data for {username}...")
    
    while current_date <= end_date:
        if current_date.weekday() in [0, 2, 4]:
            workout = Workout.objects.create(
                user=user,
                date=current_date,
                notes=f"Тренировка #{workout_count + 1}"
            )
            
            days_passed = (current_date - start_date).days
            monthly_gain = (days_passed / 30.0) * 1.0
            
            # Weighted average of weight increase + jitter
            noise = random.uniform(-0.8, 1.2)
            today_weight = round(base_weight + monthly_gain + noise, 2)
            
            workout.body_weight = today_weight
            workout.save()
            
            WeightLog.objects.create(
                user=user,
                weight=today_weight,
                date=current_date
            )
            
            # Plateau logic: stall everything in the last 15 days
            is_plateau_period = (end_date - current_date).days < 15
            
            if is_plateau_period:
                bp_weight = 80.0 
                sq_weight = 85.0
            else:
                bp_weight = 60.0 + (days_passed / 100.0) * 20.0
                sq_weight = 70.0 + (days_passed / 120.0) * 15.0
            
            WorkoutSet.objects.create(
                workout=workout,
                exercise=bench_press,
                sets=3,
                reps='10-10-10',
                weight=str(round(bp_weight, 1))
            )
            
            WorkoutSet.objects.create(
                workout=workout,
                exercise=squat,
                sets=3,
                reps='12-12-12',
                weight=str(round(sq_weight, 1))
            )
            
            if workout_count % 3 == 0:
                CardioEntry.objects.create(
                    workout=workout,
                    activity='run',
                    duration_minutes=20 + random.randint(0, 10),
                    distance_km=3.0 + random.uniform(0, 2)
                )
            
            workout_count += 1
            
        current_date += timedelta(days=1)
    
    profile.current_weight = today_weight
    profile.save()
    
    print(f"Done! Created {workout_count} workouts for {username}.")
    print(f"Final weight: {today_weight}")

if __name__ == '__main__':
    create_test_data()
