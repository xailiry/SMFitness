"""
Create a test user "demo" with 3 months of realistic workout history.
Run: python create_test_data.py
"""
import os, random
from datetime import date, timedelta
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from fitness.models import UserProfile, Exercise, Workout, WorkoutSet

# ── 1. Create test user ──
username = 'demo'
password = 'demo1234'

user, created = User.objects.get_or_create(username=username, defaults={
    'first_name': 'Демо',
    'last_name': 'Пользователь',
})
if created:
    user.set_password(password)
    user.save()
    print(f"Created user: {username} / {password}")
else:
    print(f"User '{username}' already exists, cleaning old data...")
    Workout.objects.filter(user=user).delete()

# ── 2. Set up profile ──
profile, _ = UserProfile.objects.get_or_create(user=user)
profile.height = 178
profile.current_weight = 82.5
profile.goal = 'mass'
profile.save()
print(f"Profile: 178cm, 82.5kg, цель: набор массы")

# ── 3. Define workout templates (splits) ──
exercises = {ex.name: ex for ex in Exercise.objects.all()}

# Common workout splits
PUSH_DAY = [
    ('Жим штанги лёжа', 4, 8, 70),
    ('Жим гантелей на наклонной скамье', 3, 10, 28),
    ('Разведение гантелей лёжа', 3, 12, 14),
    ('Жим штанги стоя (армейский)', 4, 8, 40),
    ('Разведение гантелей в стороны', 3, 15, 10),
    ('Французский жим лёжа', 3, 10, 30),
]

PULL_DAY = [
    ('Становая тяга', 4, 5, 100),
    ('Тяга штанги в наклоне', 4, 8, 60),
    ('Подтягивания широким хватом', 3, 10, 10),
    ('Тяга верхнего блока к груди', 3, 12, 50),
    ('Подъём штанги на бицепс стоя', 3, 10, 30),
    ('Молотковые сгибания (Молот)', 3, 12, 14),
]

LEG_DAY = [
    ('Приседания со штангой', 4, 8, 90),
    ('Жим ногами в тренажёре', 3, 10, 150),
    ('Выпады с гантелями', 3, 12, 16),
    ('Разгибание ног в тренажёре', 3, 15, 40),
    ('Сгибание ног в тренажёре', 3, 12, 35),
    ('Подъёмы на носки стоя', 4, 15, 60),
]

UPPER_BODY = [
    ('Жим гантелей лёжа', 4, 10, 30),
    ('Тяга гантели в наклоне', 4, 10, 28),
    ('Жим Арнольда', 3, 10, 18),
    ('Тяга верхнего блока к груди', 3, 12, 45),
    ('Подъём гантелей на бицепс стоя', 3, 12, 14),
    ('Разгибание рук на верхнем блоке', 3, 12, 25),
]

SPLITS = [PUSH_DAY, PULL_DAY, LEG_DAY, UPPER_BODY]

NOTES = [
    "Отличная тренировка, чувствую прогресс!",
    "Сегодня немного устал, но дотянул.",
    "Повысил рабочие веса, идёт!",
    "Лёгкая тренировка для восстановления.",
    "Новый рекорд в базовых!",
    "Фокус на технику, не гнался за весом.",
    "",
    "",
    "Пампинг-тренировка, много повторений.",
    "Силовая сессия, мало повторов — большой вес.",
]

# ── 4. Generate 3 months of data ──
today = date.today()
start_date = today - timedelta(days=90)

# Train roughly 3-4 times per week
current = start_date
split_index = 0
workouts_created = 0
week_progression = 0  # weight progression factor

while current <= today:
    # Train on Mon, Wed, Fri, Sat pattern (varies a bit)
    weekday = current.weekday()
    should_train = weekday in [0, 2, 4, 5]  # Mon, Wed, Fri, Sat

    # Random skip (~15%) for realism
    if should_train and random.random() > 0.15:
        split = SPLITS[split_index % len(SPLITS)]
        split_index += 1

        # Progressive overload: add ~1-2.5 kg every 2 weeks
        weeks_passed = (current - start_date).days // 14
        progression = weeks_passed * 2.5

        workout = Workout.objects.create(
            user=user,
            date=current,
            notes=random.choice(NOTES),
        )

        for ex_name, sets, reps, base_weight in split:
            if ex_name in exercises:
                # Add progression + small random variation
                actual_weight = base_weight + progression + random.uniform(-2, 2)
                actual_weight = round(max(5, actual_weight) * 2) / 2  # Round to nearest 0.5

                # Slight reps variation
                actual_reps = reps + random.randint(-1, 1)
                actual_reps = max(3, actual_reps)

                WorkoutSet.objects.create(
                    workout=workout,
                    exercise=exercises[ex_name],
                    sets=sets,
                    reps=actual_reps,
                    weight=actual_weight,
                )

        workouts_created += 1

    current += timedelta(days=1)

print(f"\nCreated {workouts_created} workouts over 90 days for user '{username}'")
print(f"Login: {username} / {password}")
print("Ready! Open http://127.0.0.1:8000/login/ and use these credentials.")
