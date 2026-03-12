from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

MUSCLE_GROUP_CHOICES = [
    ('chest', 'Грудь'),
    ('back', 'Спина'),
    ('shoulders', 'Плечи'),
    ('biceps', 'Бицепс'),
    ('triceps', 'Трицепс'),
    ('legs', 'Ноги'),
    ('abs', 'Пресс'),
    ('cardio', 'Кардио'),
    ('other', 'Другое'),
]

CARDIO_CHOICES = [
    ('run', 'Бег'),
    ('cycling', 'Велосипед'),
    ('swimming', 'Плавание'),
    ('rowing', 'Гребля'),
    ('elliptical', 'Эллипсоид'),
    ('jump_rope', 'Скакалка'),
    ('walk', 'Ходьба'),
    ('hiit', 'Интервальная тренировка (HIIT)'),
    ('other', 'Другое'),
]

GOAL_CHOICES = [
    ('later', 'Укажу позже'),
    ('mass', 'Набор массы'),
    ('cut', 'Похудение'),
    ('strength', 'Сила'),
    ('endurance', 'Выносливость'),
    ('health', 'Поддержание здоровья'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    height = models.PositiveIntegerField(blank=True, null=True, verbose_name="Рост (см)", validators=[MinValueValidator(100), MaxValueValidator(250)])
    current_weight = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True, verbose_name="Текущий вес (кг)", validators=[MinValueValidator(30), MaxValueValidator(500)])
    target_weight = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True, verbose_name="Целевой вес (кг)", validators=[MinValueValidator(30), MaxValueValidator(500)])
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES, blank=True, default='later', verbose_name="Цель")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Аватар")

    def __str__(self):
        return f"Профиль {self.user.username}"


class Exercise(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    muscle_group = models.CharField(max_length=20, choices=MUSCLE_GROUP_CHOICES, default='other', verbose_name="Группа мышц")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['muscle_group', 'name']


class Workout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workouts", verbose_name="Пользователь")
    date = models.DateField(verbose_name="Дата")
    notes = models.TextField(blank=True, null=True, verbose_name="Заметки")

    def __str__(self):
        return f"Тренировка {self.user.username} - {self.date}"

    class Meta:
        ordering = ['-date', '-id']

    @property
    def total_volume(self):
        """
        Total volume = sum of (sets * reps * weight) for all workout sets.
        If reps and weight are strings like '6-5-4' and '60-65-70', it sums the individual products.
        If weight is a single number and reps is a list, it multiplies each rep by that weight.
        If weight is None or is_bodyweight is True, weight is considered 0 for volume calculation.
        """
        total = 0
        for s in self.sets.all():
            if s.is_bodyweight:
                total += 0
                continue
                
            reps_str = str(s.reps).replace(',', '-').replace(' ', '-')
            reps_list = [int(r) for r in reps_str.split('-') if r.isdigit()]
            
            w_str = str(s.weight or '0').replace(',', '-').replace(' ', '-')
            w_list = [float(w) for w in w_str.split('-') if w.replace('.', '', 1).isdigit()]
            
            # If no valid reps, volume is 0
            if not reps_list:
                continue
                
            # Improved volume calculation logic
            if len(w_list) == 0:
                # No weight given, volume is 0
                continue
                
            if len(reps_list) == 1:
                # Single value for reps, multiply by number of sets
                total += reps_list[0] * s.sets * w_list[0]
            else:
                # Multiple values for reps (e.g. 10-8-6), sum them up
                for i, r in enumerate(reps_list):
                    # Use current weight from list or last available weight if list is shorter
                    current_w = w_list[i] if i < len(w_list) else w_list[-1]
                    total += r * current_w
        return total

    @property
    def total_cardio_minutes(self):
        """Sum of cardio duration for this workout."""
        return sum(c.duration_minutes for c in self.cardio_entries.all())

    @property
    def total_cardio_km(self):
        """Sum of cardio distance for this workout."""
        return sum(float(c.distance_km) for c in self.cardio_entries.all() if c.distance_km)


class WorkoutSet(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="sets", verbose_name="Тренировка")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="sets", verbose_name="Упражнение")
    sets = models.PositiveIntegerField(verbose_name="Подходы")
    reps = models.CharField(max_length=50, verbose_name="Повторения", help_text="Например: 10 или 10-8-8-6")
    weight = models.CharField(max_length=50, blank=True, null=True, verbose_name="Рабочий вес (кг)", help_text="Например: 60 или 60-65-70-75")
    is_bodyweight = models.BooleanField(default=False, verbose_name="Свой вес (Без отягощения)")

    def __str__(self):
        w = "Свой вес" if self.is_bodyweight else f"{self.weight}кг"
        return f"{self.exercise.name}: {self.sets}x{self.reps} {w}"

    def get_max_weight(self):
        """Парсит строку веса и возвращает максимальное число."""
        if self.is_bodyweight or not self.weight:
            return 0.0
        try:
            w_str = str(self.weight).replace(',', '-').replace(' ', '-')
            w_list = [float(w) for w in w_str.split('-') if w.replace('.', '', 1).isdigit()]
            return max(w_list) if w_list else 0.0
        except (ValueError, TypeError):
            return 0.0


class AIAdviceLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_logs", verbose_name="Пользователь")
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    advice_text = models.TextField(verbose_name="Текст совета")

    def __str__(self):
        return f"Совет для {self.user.username} - {self.date_created.strftime('%d.%m.%Y %H:%M')}"
    
    class Meta:
        ordering = ['-date_created']
        verbose_name = "Журнал ИИ"
        verbose_name_plural = "Журнал ИИ"


class CardioEntry(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='cardio_entries', verbose_name="Тренировка")
    activity = models.CharField(max_length=20, choices=CARDIO_CHOICES, default='run', verbose_name="Активность")
    duration_minutes = models.PositiveIntegerField(verbose_name="Длительность (мин)", validators=[MinValueValidator(1)])
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, verbose_name="Дистанция (км)", validators=[MinValueValidator(0)])
    avg_heart_rate = models.PositiveIntegerField(blank=True, null=True, verbose_name="Средний пульс (уд/мин)", validators=[MinValueValidator(30), MaxValueValidator(220)])
    calories_burned = models.PositiveIntegerField(blank=True, null=True, verbose_name="Сжжено ккал", validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True, null=True, verbose_name="Примечания")

    def __str__(self):
        return f"{self.get_activity_display()}: {self.duration_minutes} мин / {self.distance_km} км"

    @property
    def pace_per_km(self):
        """Returns pace as (min, sec) tuple if distance > 0."""
        if self.distance_km and float(self.distance_km) > 0:
            total_sec = self.duration_minutes * 60
            sec_per_km = total_sec / float(self.distance_km)
            return int(sec_per_km // 60), int(sec_per_km % 60)
        return None

    class Meta:
        ordering = ['-workout__date']
        verbose_name = "Кардио"
        verbose_name_plural = "Кардио-записи"

class WorkoutTemplate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_templates', verbose_name="Пользователь")
    name = models.CharField(max_length=100, verbose_name="Название шаблона")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Шаблон тренировки"
        verbose_name_plural = "Шаблоны тренировок"

class WorkoutTemplateExercise(models.Model):
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.CASCADE, related_name='exercises', verbose_name="Шаблон")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, verbose_name="Упражнение")
    sets_count = models.PositiveIntegerField(default=3, verbose_name="Количество подходов", validators=[MaxValueValidator(50)])
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    def __str__(self):
        return f"{self.exercise.name} ({self.sets_count} подходов)"

    class Meta:
        ordering = ['order']
        verbose_name = "Упражнение в шаблоне"
        verbose_name_plural = "Упражнения в шаблоне"
