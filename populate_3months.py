import os
import django
import random
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from fitness.models import UserProfile, Exercise, Workout, WorkoutSet, CardioEntry, MUSCLE_GROUP_CHOICES

def populate():
    username = 'pro_tester'
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password('password123')
        user.save()
    
    # Ensure profile
    profile = user.profile
    profile.height = 180
    profile.current_weight = 85.0
    profile.target_weight = 80.0
    profile.goal = 'cut'
    profile.save()

    # Base exercises
    exercises_data = [
        ('Жим лежа', 'chest'),
        ('Приседания со штангой', 'legs'),
        ('Подтягивания', 'back'),
        ('Армейский жим', 'shoulders'),
        ('Разведение гантелей', 'chest'),
        ('Тяга штанги в наклоне', 'back'),
        ('Становая тяга', 'legs'),
        ('Планка', 'abs'),
    ]
    
    exercise_objs = {}
    for name, group in exercises_data:
        ex, _ = Exercise.objects.get_or_create(name=name, defaults={'muscle_group': group})
        exercise_objs[name] = ex

    # Cardio activities
    cardio_types = ['run', 'cycling', 'walk', 'swimming']

    # Dates: last 90 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)

    print(f"Generating data for {username} from {start_date} to {end_date}...")

    # Clear old data for this user to be clean
    Workout.objects.filter(user=user).delete()

    current_date = start_date
    while current_date <= end_date:
        # 3-4 workouts per week
        if random.random() < 0.5: # ~50% chance of workout each day
            # Create Strength Workout
            workout = Workout.objects.create(user=user, date=current_date, notes=f"Тренировка за {current_date}")
            
            # 3-5 exercises per workout
            daily_exercises = random.sample(list(exercise_objs.values()), random.randint(3, 5))
            
            for ex in daily_exercises:
                # Progress logic: weight increases over time but with variance
                days_passed = (current_date - start_date).days
                base_weight = 40 + (days_passed * 0.3) # Slow progress
                
                # "Bad day" chance
                if random.random() < 0.15:
                    base_weight *= 0.8
                    reps = "8-6-4"
                else:
                    reps = "12-10-8"
                
                weight_str = f"{base_weight:.1f}-{base_weight+2.5:.1f}-{base_weight+5:.1f}"
                
                WorkoutSet.objects.create(
                    workout=workout,
                    exercise=ex,
                    sets=3,
                    reps=reps,
                    weight=weight_str,
                    is_bodyweight=False
                )

            # Cardio chance (extra days or after workout)
            if random.random() < 0.3:
                ct = random.choice(cardio_types)
                # Bad day vs good day
                is_bad_cardio = random.random() < 0.2
                duration = random.randint(15, 25) if is_bad_cardio else random.randint(35, 60)
                distance = (duration / 10.0) * (0.8 if is_bad_cardio else 1.2)
                hr = random.randint(110, 130) if is_bad_cardio else random.randint(145, 165)
                
                CardioEntry.objects.create(
                    workout=workout,
                    activity=ct,
                    duration_minutes=duration,
                    distance_km=round(distance, 2),
                    avg_heart_rate=hr,
                    calories_burned=duration * 8
                )
        
        current_date += timedelta(days=1)

    print("Success! User 'pro_tester' (pass: password123) is ready.")

if __name__ == "__main__":
    populate()
