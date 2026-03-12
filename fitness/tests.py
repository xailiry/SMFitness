from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserProfile, Exercise, Workout, WorkoutSet
from django.core.exceptions import ValidationError
from .forms import WorkoutSetForm

class SecurityAndValidationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.exercise = Exercise.objects.create(name='Test Ex', muscle_group='chest')

    def test_user_profile_signal(self):
        """Проверка автоматического создания профиля при регистрации."""
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_workout_set_validation(self):
        """Проверка строгой валидации полей reps и weight."""
        # Valid cases
        form_valid = WorkoutSetForm(data={
            'exercise': self.exercise.id,
            'sets': 3,
            'reps': '10-8-6',
            'weight': '50-55-60',
            'is_bodyweight': False
        })
        self.assertTrue(form_valid.is_valid())

        # Invalid characters
        form_invalid_chars = WorkoutSetForm(data={
            'exercise': self.exercise.id,
            'sets': 1,
            'reps': '10abc',
            'weight': '50',
            'is_bodyweight': False
        })
        self.assertFalse(form_invalid_chars.is_valid())
        self.assertIn('reps', form_invalid_chars.errors)

        # Mismatched length
        form_mismatch = WorkoutSetForm(data={
            'exercise': self.exercise.id,
            'sets': 3,
            'reps': '10-8', # Only 2 values for 3 sets
            'weight': '50',
            'is_bodyweight': False
        })
        self.assertFalse(form_mismatch.is_valid())
        self.assertIn('reps', form_mismatch.errors)
