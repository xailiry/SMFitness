import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import random
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from fitness.models import Exercise, Workout, WorkoutSet, UserProfile, MUSCLE_GROUP_CHOICES

# 1. Create/Get User
username = 'tester'
user, created = User.objects.get_or_create(username=username)
if created:
    user.set_password('password123')
    user.save()
    print(f"User {username} created.")
else:
    print(f"User {username} already exists.")

# Ensure profile settings
profile = user.profile
profile.height = 180
profile.current_weight = 85.0
profile.target_weight = 80.0
profile.goal = 'cut'
profile.save()

# 2. Setup Exercises
ex_data = [
    ('Жим лежа', 'chest'),
    ('Приседания', 'legs'),
    ('Становая тяга', 'back'),
    ('Подтягивания', 'back'),
    ('Армейский жим', 'shoulders'),
    ('Подъем на бицепс', 'biceps'),
    ('Жим гантелей', 'chest'),
]

exercises = []
for name, group in ex_data:
    ex, _ = Exercise.objects.get_or_create(name=name, defaults={'muscle_group': group})
    exercises.append(ex)

# Clear old workouts for this user to have a clean "history" for this test
Workout.objects.filter(user=user).delete()

# 3. Generate Workouts
today = date.today()

def add_workout_sets(workout, sets_list):
    for ex_obj, s, reps, weight in sets_list:
        WorkoutSet.objects.create(
            workout=workout,
            exercise=ex_obj,
            sets=s,
            reps=reps,
            weight=weight,
            is_bodyweight=(weight == 0 or weight is None)
        )

# Month 1: BAD (3 months ago to 2 months ago)
# Characteristics: Inconsistent, dropping weights, missing many days
print("Generating Month 1: Bad...")
start_m1 = today - timedelta(days=90)
for i in range(4): # 4 workouts in a month (very inconsistent)
    d = start_m1 + timedelta(days=i*7 + random.randint(0,3))
    w = Workout.objects.create(user=user, date=d, notes="Плохая тренировка, нет сил")
    # Dropping weights: 60 -> 55 -> 50
    weight = 70 - (i * 5)
    add_workout_sets(w, [
        (exercises[0], 3, "8-6-4", f"{weight}"),      # Bench
        (exercises[5], 2, "12", "10"),               # Bicep
    ])

# Month 2: NORMAL (2 months ago to 1 month ago)
# Characteristics: Stable weights, 3 times a week regularly
print("Generating Month 2: Normal...")
start_m2 = today - timedelta(days=60)
for i in range(12): # 3 times a week
    d = start_m2 + timedelta(days=(i//3)*7 + (i%3)*2)
    w = Workout.objects.create(user=user, date=d, notes="Обычная тренировка")
    
    # Static weights
    add_workout_sets(w, [
        (exercises[0], 3, "10", "60"),               # Bench 60kg
        (exercises[1], 3, "12", "80"),               # Squat 80kg
        (exercises[4], 3, "10", "40"),               # Shoulder Press 40kg
    ])

# Month 3: GOOD (Last month)
# Characteristics: Progressive overload, 4 times a week, good notes
print("Generating Month 3: Good...")
start_m3 = today - timedelta(days=30)
for i in range(16): # 4 times a week
    d = start_m3 + timedelta(days=(i//4)*7 + (i%4)*2)
    w = Workout.objects.create(user=user, date=d, notes="Отличная тренировка! Чувствую прогресс.")
    
    # Progressive weights: Bench 60 -> 80, Squat 80 -> 110
    bench_w = 60 + (i * 1.5)
    squat_w = 80 + (i * 2.0)
    dead_w = 100 + (i * 2.5) if i % 2 == 0 else 0
    
    sets = [
        (exercises[0], 4, "10-8-8-6", f"{int(bench_w)}"),
        (exercises[1], 5, "5", f"{int(squat_w)}"),
    ]
    if dead_w > 0:
        sets.append((exercises[2], 3, "5", f"{int(dead_w)}"))
    
    add_workout_sets(w, sets)

print("Done! Test account 'tester' with 3 months of data ready.")
