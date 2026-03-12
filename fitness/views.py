import os
import json
import random
from datetime import timedelta
from collections import defaultdict
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import inlineformset_factory
from django.http import JsonResponse
from django.db.models import Sum, Max, F, Count
import google.generativeai as genai
from .models import Workout, WorkoutSet, Exercise, UserProfile, MUSCLE_GROUP_CHOICES, AIAdviceLog, CardioEntry, WorkoutTemplate, WorkoutTemplateExercise
from .forms import (
    WorkoutForm, WorkoutSetForm, UserProfileForm, CardioEntryForm, 
    UsernameUpdateForm, CustomPasswordChangeForm, AvatarUpdateForm
)


def landing_page(request):
    """Landing page for unauthenticated users."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'fitness/landing.html')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('onboarding')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def generate_insights(user):
    """Генерирует список мотивационных уведомлений на основе анализа тренировок."""
    insights = []
    now = timezone.now().date()
    
    # ── 0. Целевой вес (Gamification) ──
    profile = UserProfile.objects.filter(user=user).first()
    if profile and profile.current_weight and profile.target_weight:
        diff = float(profile.current_weight) - float(profile.target_weight)
        if abs(diff) < 0.5:
            insights.append({
                'type': 'goal_reached',
                'icon': '🎉',
                'text': "Вы достигли своей цели по весу! Это потрясающий результат, продолжайте в том же духе!"
            })
        elif diff > 0 and profile.goal == 'cut':
            insights.append({
                'type': 'weight_progress',
                'icon': '📉',
                'text': f"До вашей заветной цели осталось {diff:g} кг. Продолжайте в том же духе!"
            })
        elif diff < 0 and profile.goal == 'mass':
            insights.append({
                'type': 'weight_progress',
                'icon': '📈',
                'text': f"До целевого веса осталось набрать {abs(diff):g} кг. Питание — залог успеха!"
            })
    
    # ── 1. Анализ объема (текущая неделя vs прошлая) ──
    this_week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)
    
    this_week_workouts = Workout.objects.filter(user=user, date__gte=this_week_start)
    prev_week_workouts = Workout.objects.filter(user=user, date__range=[prev_week_start, this_week_start - timedelta(days=1)])
    
    def get_volume(workouts):
        vol = 0
        for w in workouts:
            vol += w.total_volume
        return vol

    this_vol = get_volume(this_week_workouts)
    prev_vol = get_volume(prev_week_workouts)
    
    if prev_vol > 0 and this_vol > prev_vol:
        diff_pct = int(((this_vol - prev_vol) / prev_vol) * 100)
        if diff_pct >= 5:
            insights.append({
                'type': 'progress',
                'icon': '📈',
                'text': f"На этой неделе объём тренировок вырос на {diff_pct}%! Отличный прогресс!"
            })
    elif this_vol > 0 and prev_vol == 0:
         insights.append({
            'type': 'welcome',
            'icon': '💪',
            'text': "Отличное начало недели! Продолжайте в том же духе."
        })

    # ── 2. Анализ рекордов (PRs) ──
    # Оптимизация: получаем все подходы за неделю одним запросом
    recent_sets = WorkoutSet.objects.filter(
        workout__user=user, 
        workout__date__gte=now - timedelta(days=7)
    ).select_related('exercise', 'workout')
    
    exercise_ids = recent_sets.values_list('exercise_id', flat=True).distinct()
    
    # Получаем макс. веса для этих упражнений ДО текущей недели
    prev_sets_data = WorkoutSet.objects.filter(
        workout__user=user,
        exercise_id__in=exercise_ids,
        workout__date__lt=now - timedelta(days=7)
    ).values('exercise_id', 'weight', 'is_bodyweight')
    
    ex_prev_max = defaultdict(float)
    for ps in prev_sets_data:
        if ps['is_bodyweight'] or not ps['weight']:
            continue
        try:
            w_str = str(ps['weight']).replace(',', '-').replace(' ', '-')
            w_list = [float(w) for w in w_str.split('-') if w.replace('.', '', 1).isdigit()]
            if w_list:
                m = max(w_list)
                if m > ex_prev_max[ps['exercise_id']]:
                    ex_prev_max[ps['exercise_id']] = m
        except (ValueError, TypeError):
            continue

    for rset in recent_sets:
        prev_max = ex_prev_max[rset.exercise_id]
        current_max = rset.get_max_weight()
        
        if prev_max > 0 and current_max > prev_max:
             diff_weight = current_max - prev_max
             insights.append({
                'type': 'record',
                'icon': '🏆',
                'text': f"Новый рекорд: «{rset.exercise.name}»! Вы прибавили {diff_weight:g} кг."
            })
             break # Один рекорд для краткости

    # ── 3. Серия тренировок (streak) ──
    # Unify with dashboard logic
    def calculate_streak(user_obj):
        all_w = Workout.objects.filter(user=user_obj).order_by('-date')
        if not all_w.exists(): return 0
        
        today = timezone.now().date()
        # Start of current calendar week (Monday)
        week_start = today - timedelta(days=today.weekday())
        
        # Check if there is a workout this week
        has_this_week = all_w.filter(date__gte=week_start).exists()
        
        streak = 0
        current_ws = week_start
        
        if not has_this_week:
            # Check if there was a workout last week to keep streak alive
            last_week_start = week_start - timedelta(days=7)
            if not all_w.filter(date__range=[last_week_start, week_start - timedelta(days=1)]).exists():
                return 0
            current_ws = last_week_start # Start counting from last week

        while True:
            next_ws = current_ws - timedelta(days=7)
            if all_w.filter(date__range=[current_ws, current_ws + timedelta(days=6)]).exists():
                streak += 1
                current_ws = next_ws
            else:
                break
        return streak

    weeks_count = calculate_streak(user)
    
    if weeks_count >= 2: # Show even for 2 weeks
        insights.append({
            'type': 'streak',
            'icon': '🔥',
            'text': f"Вы тренируетесь уже {weeks_count} недели подряд! Крутая стабильность."
        })

    # ── 4. Любимое упражнение за месяц ──
    month_ago = now - timedelta(days=30)
    favorite_exercise = WorkoutSet.objects.filter(
        workout__user=user, workout__date__gte=month_ago
    ).values('exercise__name').annotate(
        total_sets=Sum('sets')
    ).order_by('-total_sets').first()

    if favorite_exercise and favorite_exercise['total_sets'] >= 10:
        insights.append({
            'type': 'favorite',
            'icon': '⭐',
            'text': f"Ваше любимое упражнение месяца — «{favorite_exercise['exercise__name']}» ({favorite_exercise['total_sets']} подходов)."
        })

    # ── 5. Кардио прогресс (Минуты) ──
    this_week_cardio = CardioEntry.objects.filter(workout__user=user, workout__date__gte=this_week_start).aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0
    prev_week_cardio = CardioEntry.objects.filter(workout__user=user, workout__date__range=[prev_week_start, this_week_start - timedelta(days=1)]).aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0

    if prev_week_cardio > 0 and this_week_cardio > prev_week_cardio:
        insights.append({
            'type': 'cardio',
            'icon': '🏃',
            'text': f"На этой неделе вы сделали на {this_week_cardio - prev_week_cardio} мин. больше кардио, чем на прошлой!"
        })

    # ── 6. Разнообразие тренировок ──
    # Сколько уникальных групп мышц задействовано за последние 7 дней?
    recent_muscles = WorkoutSet.objects.filter(
        workout__user=user, workout__date__gte=this_week_start
    ).values('exercise__muscle_group').distinct().count()

    if recent_muscles >= 5:
         insights.append({
            'type': 'variety',
            'icon': '🧩',
            'text': f"Гармоничное развитие! За неделю вы проработали {recent_muscles} разных групп мышц."
        })

    # ── 7. Легендарные вехи по объему (Тонны) ──
    # Оптимизация: используем предвычисленный объем, если бы он был в БД, 
    # но пока считаем эффективно через prefetch в вызывающем коде или здесь.
    all_workouts = Workout.objects.filter(user=user).prefetch_related('sets')
    total_lifetime_volume = sum(w.total_volume for w in all_workouts) / 1000.0 # В тоннах
    
    milestones = [10, 50, 100, 250, 500, 1000, 2000, 5000]
    # Находим самую большую достигнутую веху
    reached_milestone = 0
    for m in milestones:
        if total_lifetime_volume >= m:
            reached_milestone = m
        else:
            break
            
    if reached_milestone > 0:
        # Показываем инсайт только если мы "недавно" (в пределах последних 10% или 5 тонн) достигли этой вехи
        # Это предотвращает постоянный показ старых вех.
        threshold = max(reached_milestone * 0.05, 5.0)
        if total_lifetime_volume < reached_milestone + threshold:
            insights.append({
                'type': 'milestone',
                'icon': '👑',
                'text': f"Невероятно! За всё время вы подняли уже более {reached_milestone} тонн железа!"
            })

    # Ограничить отдачу до 4 интересных инсайтов случайным образом, но приоритет важным
    if len(insights) > 4:
        random.shuffle(insights)
        insights = insights[:4]

    return insights


@login_required
def profile(request):
    profile_instance, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Forms initialization
    form = UserProfileForm(instance=profile_instance)
    username_form = UsernameUpdateForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            form = UserProfileForm(request.POST, request.FILES, instance=profile_instance)
            if form.is_valid():
                form.save()
                messages.success(request, "Профиль успешно обновлен!")
                return redirect('profile')
        
        elif action == 'update_avatar':
            avatar_form = AvatarUpdateForm(request.POST, request.FILES, instance=profile_instance)
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, "Аватар успешно обновлен!")
                return redirect('profile')
                
        elif action == 'update_username':
            username_form = UsernameUpdateForm(request.POST, instance=request.user)
            if username_form.is_valid():
                username_form.save()
                messages.success(request, "Имя пользователя успешно изменено!")
                return redirect('profile')
            else:
                messages.error(request, "Ошибка при смене логина. Проверьте введенные данные.")
                
        elif action == 'update_password':
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Keep the user logged in
                messages.success(request, "Пароль успешно изменен!")
                return redirect('profile')
            else:
                messages.error(request, "Ошибка при смене пароля. Убедитесь в правильности старого пароля и соблюдении требований.")

    total_workouts = Workout.objects.filter(user=request.user).count()
    days_since = (timezone.now().date() - request.user.date_joined.date()).days

    bmi = None
    bmi_category = None
    if profile_instance.height and profile_instance.current_weight:
        h_m = float(profile_instance.height) / 100.0
        bmi_val = float(profile_instance.current_weight) / (h_m * h_m)
        bmi = round(bmi_val, 1)
        if bmi < 18.5:
            bmi_category = "Недостаточный вес"
        elif 18.5 <= bmi < 25:
            bmi_category = "Норма"
        elif 25 <= bmi < 30:
            bmi_category = "Избыточный вес"
        else:
            bmi_category = "Ожирение"

    user_templates = WorkoutTemplate.objects.filter(user=request.user).prefetch_related('exercises__exercise')

    return render(request, 'fitness/profile.html', {
        'form': form,
        'username_form': username_form,
        'password_form': password_form,
        'profile': profile_instance,
        'total_workouts': total_workouts,
        'days_since': days_since,
        'bmi': bmi,
        'bmi_category': bmi_category,
        'user_templates': user_templates,
    })


@login_required
def dashboard(request):
    # Enforce onboarding
    try:
        profile = request.user.profile
        if not profile.height or not profile.current_weight:
            return redirect('onboarding')
    except UserProfile.DoesNotExist:
        return redirect('onboarding')

    # Check if we should show the interactive tutorial
    show_tutorial = request.session.pop('show_tutorial', False)

    workouts = Workout.objects.filter(user=request.user).prefetch_related('sets__exercise', 'cardio_entries')[:10]
    all_workouts = Workout.objects.filter(user=request.user).prefetch_related('sets__exercise', 'cardio_entries')

    # Calculate BMI
    bmi = None
    bmi_category = None
    bmi_hue = None
    try:
        if profile.height and profile.current_weight:
            h_m = float(profile.height) / 100.0
            bmi_val = float(profile.current_weight) / (h_m * h_m)
            bmi = round(bmi_val, 1)
            
            if bmi < 18.5:
                bmi_category = "Недостаточный вес"
            elif 18.5 <= bmi < 25:
                bmi_category = "Норма"
            elif 25 <= bmi < 30:
                bmi_category = "Избыточный вес"
            else:
                bmi_category = "Ожирение"

            # Calculate Hue for dynamic gradient (0 = red, 45 = yellow, 135 = green)
            # Ideal BMI ~22 -> Hue 135
            # BMI 30+ -> Hue 0
            # BMI 15- -> Hue 0
            if bmi >= 22:
                excess = min(max((bmi - 22) / 8.0, 0), 1)
                bmi_hue = int(135 * (1 - excess))
            else:
                deficit = min(max((22 - bmi) / 7.0, 0), 1)
                bmi_hue = int(135 * (1 - deficit))
                
    except Exception:
        pass

    # Weight Goal Progress (Gamification)
    weight_progress_pct = None
    weight_goal_reached = False
    if profile.current_weight and profile.target_weight:
        # Check initial weight from first workout or registrations (simplified: use first weight ever recorded vs current)
        # For simplicity, if they entered goal, we show progress.
        # Let's say we use a simple scale: if goal is to lose weight, then current weight vs target.
        # We need a 'starting weight' to show real progress bar 0-100%.
        # For now, let's just use it as "current distance to goal" if we don't have starting weight.
        # Or better: let's assume progress is based on some reasonable delta.
        # Actually, the user asked to "обыграть это".
        
        # Let's try to find the very first recorded weight for this user
        first_weight_record = Workout.objects.filter(user=request.user).order_by('date').first()
        # If no workouts yet, start weight is the weight they registered with??
        # But current_weight updates. So we might need a separate field for 'initial_weight'.
        # For now: if mass goal: pct = (current / target) * 100. If cut goal: pct = (target / current) * 100.
        
        curr = float(profile.current_weight)
        target = float(profile.target_weight)
        weight_diff = round(abs(curr - target), 1)
        
        if profile.goal == 'cut':
            if curr <= target:
                weight_progress_pct = 100
                weight_goal_reached = True
            else:
                # Use a 10kg window for a more "active" progress bar if no history, 
                # but better to keep it simple as requested
                weight_progress_pct = max(0, min(100, int((target / curr) * 100)))
        elif profile.goal == 'mass':
            if curr >= target:
                weight_progress_pct = 100
                weight_goal_reached = True
            else:
                weight_progress_pct = max(0, min(100, int((curr / target) * 100)))
        else:
            weight_progress_pct = 100 if weight_diff < 0.5 else int((min(curr, target) / max(curr, target)) * 100)
            if weight_diff < 0.5: weight_goal_reached = True

    # ── Stats cards ──
    total_workouts = all_workouts.count()

    # ── Consolidated processing for Dashboard ──
    raw_sets = []
    total_volume = 0
    max_val = 0.0
    best_lift = None

    for workout in all_workouts:
        for s in workout.sets.all():
            reps_str = str(s.reps).replace(',', '-').replace(' ', '-')
            rep_parts = [int(r) for r in reps_str.split('-') if r.isdigit()]
            
            w_str = str(s.weight or '0').replace(',', '-').replace(' ', '-')
            w_list = [float(wt) for wt in w_str.split('-') if wt.replace('.', '', 1).isdigit()]
            max_w = s.get_max_weight()

            # Volume calculation for this set
            v = 0.0
            if rep_parts:
                if s.is_bodyweight:
                    v = 0.0
                elif len(rep_parts) > 1 and len(w_list) == 1:
                    v = sum(rep_parts) * w_list[0]
                elif len(rep_parts) > 1 and len(w_list) > 1:
                    v = sum(r * wt for r, wt in zip(rep_parts, w_list))
                elif len(rep_parts) == 1 and len(w_list) == 1:
                    v = s.sets * rep_parts[0] * w_list[0]
                elif len(rep_parts) == 1 and len(w_list) > 1:
                    v = rep_parts[0] * sum(w_list)
            
            total_volume += v
            
            # Best lift tracking
            if not s.is_bodyweight and max_w > max_val:
                max_val = max_w
                best_lift = {'exercise': s.exercise.name, 'weight': max_w}

            raw_sets.append({
                'd': workout.date.strftime('%Y-%m-%d'),
                'e': str(s.exercise.name),
                'm': str(s.exercise.muscle_group),
                'w': float(max_w),
                'v': float(v),
                'sets': len(rep_parts) if rep_parts else int(s.sets)
            })
    
    total_volume_tons = total_volume / 1000

    # Streak: consecutive weeks with at least 1 workout
    # Better logic: if no workout this week, check last week to maintain streak
    streak = 0
    if total_workouts > 0:
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        # In-memory check using all_workouts (which is already fetched)
        has_this_week = any(w.date >= week_start for w in all_workouts)
        
        curr_ws = week_start
        if not has_this_week:
            # Check last week
            last_ws = week_start - timedelta(days=7)
            if any(last_ws <= w.date < week_start for w in all_workouts):
                curr_ws = last_ws
            else:
                curr_ws = None # Streak is 0

        if curr_ws:
            while True:
                if any(curr_ws <= w.date <= curr_ws + timedelta(days=6) for w in all_workouts):
                    streak += 1
                    curr_ws -= timedelta(days=7)
                else:
                    break

    # ── Chart data: supply raw data for JS charting (similar to statistics) ──
    raw_sets = []
    for workout in all_workouts:
        for s in workout.sets.all():
            
            reps_str = str(s.reps).replace(',', '-').replace(' ', '-')
            rep_parts = [int(r) for r in reps_str.split('-') if r.isdigit()]
            
            w_str = str(s.weight or '0').replace(',', '-').replace(' ', '-')
            w_list = [float(wt) for wt in w_str.split('-') if wt.replace('.', '', 1).isdigit()]
            max_w = s.get_max_weight()

            if not rep_parts or s.is_bodyweight:
                v = 0.0
            elif len(rep_parts) > 1 and len(w_list) == 1:
                v = sum(rep_parts) * w_list[0]
            elif len(rep_parts) > 1 and len(w_list) > 1:
                v = sum(r * wt for r, wt in zip(rep_parts, w_list))
            elif len(rep_parts) == 1 and len(w_list) == 1:
                v = s.sets * rep_parts[0] * w_list[0]
            elif len(rep_parts) == 1 and len(w_list) > 1:
                v = rep_parts[0] * sum(w_list)
            else:
                v = 0.0
            
            raw_sets.append({
                'd': workout.date.strftime('%Y-%m-%d'),
                'e': str(s.exercise.name),
                'm': str(s.exercise.muscle_group),
                'w': float(max_w),
                'v': float(v),
                'sets': len(rep_parts) if rep_parts else int(s.sets)
            })
            
    raw_cardio = []
    for c in CardioEntry.objects.filter(workout__user=request.user).select_related('workout'):
        raw_cardio.append({
            'd': c.workout.date.strftime('%Y-%m-%d'),
            'm': c.duration_minutes,
            'k': float(c.distance_km) if c.distance_km else 0.0
        })

    # ── Cardio totals ──
    cardio_totals = CardioEntry.objects.filter(workout__user=request.user).aggregate(
        total_minutes=Sum('duration_minutes'),
        total_km=Sum('distance_km'),
    )
    total_cardio_minutes = cardio_totals['total_minutes'] or 0
    total_cardio_km = float(cardio_totals['total_km'] or 0)

    exercises = Exercise.objects.all()

    quotes = [
        {"text": "Тело достигает того, во что верит разум.", "author": "Джим Рон"},
        {"text": "Дисциплина — это мост между целями и достижениями.", "author": "Джим Рон"},
        {"text": "Большинство людей терпят неудачу не потому, что целятся слишком высоко и промахиваются, а потому, что целятся слишком низко и попадают.", "author": "Лес Браун"},
        {"text": "Тот, кто переносит гору, начинает с того, что переносит мелкие камни.", "author": "Конфуций"},
        {"text": "Если вы хотите иметь то, чего никогда не имели, вам придется делать то, чего вы никогда не делали.", "author": "Коко Шанель"},
        {"text": "Только те, кто рискует зайти слишком далеко, могут узнать, как далеко можно зайти.", "author": "Томас Элиот"},
        {"text": "В падающем самолете сначала надень маску на себя, потом на ребенка. Так же и в жизни.", "author": "Неизвестный автор"},
        {"text": "Нельзя тренироваться один день и ждать результатов. Нужно постоянство.", "author": "Брюс Ли"},
        {"text": "Победа любит подготовку.", "author": "Древнеримская пословица"},
        {"text": "Тренировка — это не то, что ты делаешь, а то, кем ты становишься.", "author": "Арнольд Шварценеггер"},
        {"text": "Сложно — не значит невозможно.", "author": "Неизвестный автор"},
        {"text": "Ваше тело — единственный дом, в котором вам суждено прожить всю жизнь. Берегите его.", "author": "Джим Рон"},
        {"text": "Единственная плохая тренировка — та, которой не было.", "author": "Неизвестный автор"},
        {"text": "Через год вы будете жалеть, что не начали сегодня.", "author": "Карен Лэмб"},
        {"text": "Работа над собой — самая сложная работа, но она приносит самые большие плоды.", "author": "Неизвестный автор"},
        {"text": "Сила не в мышцах, а в характере.", "author": "Неизвестный автор"},
        {"text": "То, что кажется сегодня невозможным, завтра станет твоей разминкой.", "author": "Неизвестный автор"},
        {"text": "Ваш прогресс начинается там, где заканчивается зона комфорта.", "author": "Нил Доналд Уолш"},
        {"text": "Мотивация помогает начать. Дисциплина заставляет продолжать.", "author": "Джим Рон"},
        {"text": "Успех — это сумма маленьких усилий, повторяющихся изо дня в день.", "author": "Роберт Кольер"},
        {"text": "Не так важно, насколько медленно вы идете, пока вы не останавливаетесь.", "author": "Конфуций"},
        {"text": "Лучшее время, чтобы посадить дерево, было 20 лет назад. Следующее лучшее время — сегодня.", "author": "Китайская пословица"},
        {"text": "Будь сильнее своих оправданий.", "author": "Неизвестный автор"},
        {"text": "Здоровье — это не цель, это путь.", "author": "Неизвестный автор"},
        {"text": "Ты сам создаешь свой лимит.", "author": "Неизвестный автор"},
        {"text": "Каждая тренировка — это шаг к лучшей версии себя.", "author": "Неизвестный автор"},
        {"text": "Не сравнивай себя с другими. Сравнивай себя с тем, кем ты был вчера.", "author": "Неизвестный автор"},
        {"text": "Маленькие шаги приводят к большим результатам.", "author": "Неизвестный автор"},
        {"text": "Никогда не сдавайся, и ты увидишь, как сдаются другие.", "author": "Неизвестный автор"},
    ]
    daily_quote = random.choice(quotes)

    CHART_MIN_WORKOUTS = 3
    show_charts = total_workouts >= CHART_MIN_WORKOUTS

    context = {
        'workouts': workouts,
        'exercises': exercises,
        'raw_sets_json': json.dumps(raw_sets),
        'raw_cardio_json': json.dumps(raw_cardio),
        'total_workouts': total_workouts,
        'total_volume_tons': round(float(total_volume_tons), 2),
        'best_lift': best_lift,
        'streak': streak,
        'bmi': bmi,
        'bmi_category': bmi_category,
        'bmi_hue': bmi_hue,
        'show_tutorial': show_tutorial,
        'daily_quote': daily_quote,
        'total_cardio_minutes': total_cardio_minutes,
        'total_cardio_km': round(total_cardio_km, 1),
        'insights': generate_insights(request.user),
        'show_charts': show_charts,
        'min_workouts': CHART_MIN_WORKOUTS,
        'weight_progress_pct': weight_progress_pct,
        'weight_goal_reached': weight_goal_reached,
        'weight_diff': weight_diff if 'weight_diff' in locals() else None,
        'target_weight': profile.target_weight if 'profile' in locals() else None,
    }
    return render(request, 'fitness/dashboard.html', context)


@login_required
def statistics(request):
    all_workouts = Workout.objects.filter(user=request.user).prefetch_related('sets__exercise', 'cardio_entries')

    # ── 1. Weight progress (reuse) ──
    chart_data2 = {}
    for workout in all_workouts:
        date_str = workout.date.strftime('%Y-%m-%d')
        for s in workout.sets.all():
            ex_name = str(s.exercise.name)
            ex_dict = chart_data2.get(ex_name, {})
            current_w = ex_dict.get(date_str, 0.0)
            
            w_weight = s.get_max_weight()
            
            if w_weight > float(current_w):
                ex_dict[date_str] = w_weight
            chart_data2[ex_name] = ex_dict
    
    sorted_chart_data2 = {}
    for ex in chart_data2:
        sorted_chart_data2[ex] = dict(sorted(chart_data2[ex].items()))
    chart_data2 = sorted_chart_data2

    # ── Unified data processing for Statistics ──
    weekly_volume_raw = defaultdict(float)
    weekday_freq = [0] * 7
    muscle_dist = {}
    muscle_labels_map = dict(MUSCLE_GROUP_CHOICES)
    raw_sets = []

    for w in all_workouts:
        # Weekday freq
        weekday_freq[w.date.weekday()] += 1
        
        # ISO week key
        iso = w.date.isocalendar()
        wk_key = f"{iso[0]}-W{iso[1]:02d}"
        
        for s in w.sets.all():
            # Parse reps and weight once
            reps_str = str(s.reps).replace(',', '-').replace(' ', '-')
            rep_parts = [int(r) for r in reps_str.split('-') if r.isdigit()]
            total_reps = sum(rep_parts) if rep_parts else 0
            
            w_str = str(s.weight or '0').replace(',', '-').replace(' ', '-')
            w_list = [float(wt) for wt in w_str.split('-') if wt.replace('.', '', 1).isdigit()]
            max_w = s.get_max_weight()

            # Volume calculation
            v = 0.0
            if rep_parts:
                if s.is_bodyweight:
                    v = 0.0
                elif len(rep_parts) > 1 and len(w_list) == 1:
                    v = total_reps * w_list[0]
                elif len(rep_parts) > 1 and len(w_list) > 1:
                    v = sum(r * wt for r, wt in zip(rep_parts, w_list))
                elif len(rep_parts) == 1 and len(w_list) == 1:
                    v = s.sets * rep_parts[0] * w_list[0]
                elif len(rep_parts) == 1 and len(w_list) > 1:
                    v = rep_parts[0] * sum(w_list)
            
            weekly_volume_raw[wk_key] += v
            
            # Muscle group dist
            group = s.exercise.muscle_group
            label = str(muscle_labels_map.get(group, group))
            muscle_dist[label] = muscle_dist.get(label, 0) + total_reps
            
            # Raw sets for JS
            raw_sets.append({
                'd': w.date.strftime('%Y-%m-%d'),
                'e': s.exercise.name,
                'm': label,
                'v': float(v),
                'w': float(max_w),
                'r': total_reps,
                'sets': len(rep_parts) if rep_parts else int(s.sets)
            })

    # Weekly volume labels/values
    sorted_keys = sorted(weekly_volume_raw.keys())
    weekly_volume_labels = []
    weekly_volume_values = []
    from datetime import date
    for k in sorted_keys:
        y, wn = int(k[:4]), int(k[6:])
        d = date.fromisocalendar(y, wn, 1)
        start_str = d.strftime('%d.%m')
        end_str = (d + timedelta(days=6)).strftime('%d.%m')
        weekly_volume_labels.append(f"Неделя {wn} ({start_str}-{end_str})")
        weekly_volume_values.append(weekly_volume_raw[k])

    # ── 5. Cardio weekly minutes + distance ──
    cardio_weekly_minutes_raw = defaultdict(int)
    cardio_weekly_km_raw = defaultdict(float)
    all_cardio = CardioEntry.objects.filter(workout__user=request.user).select_related('workout')
    for c in all_cardio:
        iso = c.workout.date.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        cardio_weekly_minutes_raw[wk] += c.duration_minutes
        cardio_weekly_km_raw[wk] += float(c.distance_km or 0)
    
    # fill both dicts with same sorted keys
    all_wks_sorted = sorted(set(list(cardio_weekly_minutes_raw.keys()) + list(cardio_weekly_km_raw.keys())))
    cardio_labels = []
    cardio_minutes_values = []
    cardio_km_values = []
    
    from datetime import date
    for k in all_wks_sorted:
        y, wn = int(k[:4]), int(k[6:])
        d = date.fromisocalendar(y, wn, 1)
        start_str = d.strftime('%d.%m')
        end_str = (d + timedelta(days=6)).strftime('%d.%m')
        
        cardio_labels.append(f"Нед {wn} ({start_str})") # Shorter for cardio chart maybe?
        cardio_minutes_values.append(cardio_weekly_minutes_raw[k])
        cardio_km_values.append(round(cardio_weekly_km_raw[k], 2))

    # Raw data for JS filtering
    raw_sets = []
    for w in all_workouts:
        for s in w.sets.all():
            reps_str = str(s.reps).replace(',', '-').replace(' ', '-')
            rep_parts = [int(r) for r in reps_str.split('-') if r.isdigit()]
            total_reps = sum(rep_parts) if rep_parts else 0
            
            w_str = str(s.weight or '0').replace(',', '-').replace(' ', '-')
            w_list = [float(wt) for wt in w_str.split('-') if wt.replace('.', '', 1).isdigit()]
            max_w = s.get_max_weight()

            if not rep_parts or s.is_bodyweight:
                v = 0.0
            elif len(rep_parts) > 1 and len(w_list) == 1:
                v = sum(rep_parts) * w_list[0]
            elif len(rep_parts) > 1 and len(w_list) > 1:
                v = sum(r * wt for r, wt in zip(rep_parts, w_list))
            elif len(rep_parts) == 1 and len(w_list) == 1:
                v = s.sets * rep_parts[0] * w_list[0]
            elif len(rep_parts) == 1 and len(w_list) > 1:
                v = rep_parts[0] * sum(w_list)
            else:
                v = 0.0
            
            raw_sets.append({
                'd': w.date.strftime('%Y-%m-%d'),
                'e': s.exercise.name,
                'm': str(muscle_labels_map.get(s.exercise.muscle_group, s.exercise.muscle_group)),
                'v': float(v),
                'w': float(max_w),
                'r': total_reps,
                'sets': len(rep_parts) if rep_parts else int(s.sets)
            })
    
    raw_cardio = []
    for c in all_cardio:
        raw_cardio.append({
            'd': c.workout.date.strftime('%Y-%m-%d'),
            'min': c.duration_minutes,
            'km': float(c.distance_km or 0)
        })

    CHART_MIN_WORKOUTS = 3
    total_workouts = all_workouts.count()
    show_charts = total_workouts >= CHART_MIN_WORKOUTS

    context = {
        'has_data': all_workouts.exists(),
        'has_cardio': all_cardio.exists(),
        'show_charts': show_charts,
        'min_workouts': CHART_MIN_WORKOUTS,
        'raw_sets_json': json.dumps(raw_sets),
        'raw_cardio_json': json.dumps(raw_cardio),
    }
    return render(request, 'fitness/statistics.html', context)


@login_required
def add_workout(request):
    WorkoutSetFormSet = inlineformset_factory(
        Workout, WorkoutSet, form=WorkoutSetForm, extra=1, can_delete=False
    )
    CardioFormSet = inlineformset_factory(
        Workout, CardioEntry, form=CardioEntryForm, extra=1, can_delete=False
    )
    if request.method == 'POST':
        workout_form = WorkoutForm(request.POST)
        if workout_form.is_valid():
            workout = workout_form.save(commit=False)
            workout.user = request.user
            formset = WorkoutSetFormSet(request.POST, instance=workout)
            cardio_formset = CardioFormSet(request.POST, instance=workout, prefix='cardio')
            if formset.is_valid() and cardio_formset.is_valid():
                workout.save()
                formset.save()
                # Only save cardio forms that have actual data
                for cform in cardio_formset:
                    if cform.cleaned_data.get('duration_minutes'):
                        cform.save()
                return redirect('dashboard')
    else:
        workout_form = WorkoutForm()
        formset = WorkoutSetFormSet()
        cardio_formset = CardioFormSet(prefix='cardio')

    # Pass exercise -> muscle group mapping to frontend
    exercises = Exercise.objects.all()
    exercises_dict = {ex.id: ex.muscle_group for ex in exercises}
    user_templates = WorkoutTemplate.objects.filter(user=request.user).prefetch_related('exercises__exercise')

    return render(request, 'fitness/workout_form.html', {
        'workout_form': workout_form,
        'formset': formset,
        'cardio_formset': cardio_formset,
        'exercises_json': json.dumps(exercises_dict),
        'user_templates': user_templates,
    })


@login_required
def workout_detail(request, pk):
    workout = get_object_or_404(Workout.objects.prefetch_related('sets__exercise', 'cardio_entries'), pk=pk, user=request.user)
    return render(request, 'fitness/workout_detail.html', {'workout': workout})


@login_required
def delete_workout(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    if request.method == 'POST':
        workout.delete()
        return redirect('dashboard')
    return redirect('dashboard')


@login_required
def get_ai_recommendation(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Только POST запросы'}, status=400)

    # 1. Лимиты и Кулдаун
    now = timezone.now()
    
    # Кулдаун 3 минуты
    last_log = AIAdviceLog.objects.filter(user=request.user).first()
    if last_log:
        diff = now - last_log.date_created
        if diff.total_seconds() < 180: # 3 минуты
            remaining = int(180 - diff.total_seconds())
            return JsonResponse({'error': f'Слишком часто! Подождите еще {remaining} сек.'}, status=429)

    # Лимит 3 в месяц
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_count = AIAdviceLog.objects.filter(user=request.user, date_created__gte=month_start).count()
    if month_count >= 3:
        return JsonResponse({'error': 'Вы исчерпали лимит советов на этот месяц (макс. 3).'}, status=429)

    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    workouts = Workout.objects.filter(user=request.user, date__gte=thirty_days_ago).prefetch_related('sets__exercise', 'cardio_entries')
    
    if Workout.objects.filter(user=request.user).count() < 3:
        return JsonResponse({'error': 'Для получения советов от ИИ необходимо провести минимум 3 тренировки.'}, status=400)

    if not workouts.exists():
        return JsonResponse({'recommendation': 'У вас пока нет тренировок за последние 30 дней. Начните тренироваться, чтобы получить совет!'})

    # Profile context
    profile_info = ""
    try:
        p = request.user.profile
        goal_display = p.get_goal_display()
        target_str = f", целевой вес {p.target_weight} кг" if p.target_weight else ""
        profile_info = f"Данные пользователя: рост {p.height or '?'} см, вес {p.current_weight or '?'} кг{target_str}, цель: {goal_display}.\n"
    except UserProfile.DoesNotExist:
        pass

    history = []
    for w in workouts:
        day_str = str(f"Дата: {w.date}")
        history.append(day_str)
        history.append(str(f"  Объем: {w.total_volume} кг"))
        if w.notes:
            history.append(str(f"  Заметки: {w.notes}"))
        for s in w.sets.all():
            history.append(str(f"    - {s.exercise.name}: {s.sets}x{s.reps} ({s.weight} кг)"))
        # Cardio entries for this workout
        for c in w.cardio_entries.all():
            pace_str = ''
            if c.pace_per_km:
                pace_str = f", темп: {c.pace_per_km[0]}:{c.pace_per_km[1]:02d} мин/км"
            hr_str = f", ЧСС: {c.avg_heart_rate} уд/мин" if c.avg_heart_rate else ''
            cal_str = f", {c.calories_burned} ккал" if c.calories_burned else ''
            dist_str = f", {c.distance_km} км" if c.distance_km else ''
            history.append(str(f"    [Кардио] {c.get_activity_display()}: {c.duration_minutes} мин{dist_str}{pace_str}{hr_str}{cal_str}"))

    # Check if user does any cardio at all
    has_any_cardio = CardioEntry.objects.filter(workout__user=request.user).exists()
    cardio_note = (
        '' if has_any_cardio
        else "ВАЖНО: пользователь не записывает кардио-тренировки. Обязательно упомяни это и дай рекомендацию по включению кардио в план.\n"
    )

    history_text = "\n".join(history)

    prompt = (
        "Ты профессиональный фитнес-тренер. Ниже приведена история тренировок пользователя за 30 дней.\n"
        f"{profile_info}"
        f"{cardio_note}"
        "Проанализируй прогресс и дай краткий, мотивирующий совет по дальнейшим тренировкам, на чем сделать акцент. "
        "Укажи конкретные рекомендации по весам и повторениям. Пиши на русском языке, 4-6 предложений.\n\n"
        f"История:\n" + history_text
    )

    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return JsonResponse({'recommendation': 'API ключ Gemini не настроен.'})

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt, request_options={"timeout": 15})
        
        advice = response.text
        
        # Save to database
        AIAdviceLog.objects.create(
            user=request.user,
            advice_text=advice
        )

        return JsonResponse({'recommendation': advice})
    except Exception as e:
        return JsonResponse({'recommendation': f'Произошла ошибка при обращении к ИИ: {str(e)}'})

@login_required
def ai_journal(request):
    logs = AIAdviceLog.objects.filter(user=request.user)
    
    # Считаем остаток лимитов
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_count = AIAdviceLog.objects.filter(user=request.user, date_created__gte=month_start).count()
    remaining_attempts = max(0, 3 - month_count)
    
    return render(request, 'fitness/ai_journal.html', {
        'logs': logs,
        'remaining_attempts': remaining_attempts,
        'limit_total': 3
    })

@login_required
def onboarding_view(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # If already onboarded, send to dashboard
    if user_profile.height and user_profile.current_weight:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            # Set a flag in session to show the interactive tutorial on the dashboard
            request.session['show_tutorial'] = True
            return redirect('dashboard')
    else:
        # Default choices
        form = UserProfileForm(instance=user_profile)
        
    return render(request, 'fitness/onboarding.html', {'form': form})

@login_required
def save_as_template(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    if request.method == 'POST':
        # Get custom name from post or use default
        default_name = f"Шаблон: {workout.date.strftime('%d.%m.%Y')} - Тренировка"
        custom_name = request.POST.get('template_name', default_name)
        
        # Create template
        template = WorkoutTemplate.objects.create(
            user=request.user,
            name=custom_name
        )
        
        # Aggregate exercises
        exercises_data = defaultdict(int)
        for wset in workout.sets.all():
            exercises_data[wset.exercise] += 1
            
        order = 0
        for exercise, count in exercises_data.items():
            WorkoutTemplateExercise.objects.create(
                template=template,
                exercise=exercise,
                sets_count=count,
                order=order
            )
            order += 1
            
        return redirect('profile')
    return redirect('workout_detail', pk=pk)

@login_required
def api_get_template(request, pk):
    template = get_object_or_404(WorkoutTemplate, pk=pk, user=request.user)
    exercises = []
    for te in template.exercises.all().order_by('order'):
        exercises.append({
            'exercise_id': te.exercise.id,
            'exercise_name': te.exercise.name,
            'sets_count': te.sets_count
        })
    return JsonResponse({'exercises': exercises})

@login_required
def delete_template(request, pk):
    template = get_object_or_404(WorkoutTemplate, pk=pk, user=request.user)
    if request.method == 'POST':
        template.delete()
        return redirect('profile')
    return redirect('profile')

@login_required
def rename_template(request, pk):
    template = get_object_or_404(WorkoutTemplate, pk=pk, user=request.user)
    if request.method == 'POST':
        new_name = request.POST.get('name')
        if new_name:
            template.name = new_name
            template.save()
            return JsonResponse({'status': 'ok', 'new_name': template.name})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def template_detail(request, pk):
    template = get_object_or_404(WorkoutTemplate.objects.prefetch_related('exercises__exercise'), pk=pk, user=request.user)
    return render(request, 'fitness/template_detail.html', {'template': template})


@login_required
def workout_archive(request):
    """
    Страница архива. Группирует только структуру (года и недели) с количеством тренировок.
    """
    profile = UserProfile.objects.filter(user=request.user).first()
    # Агрегируем данные по тренировкам
    workouts = Workout.objects.filter(user=request.user).order_by('-date')
    
    archive_data = {} # {year: {week_num: count}}
    
    for w in workouts:
        iso_year, week_num, _ = w.date.isocalendar()
        # Используем ISO-год для синхронизации с ISO-неделями
        if iso_year not in archive_data:
            archive_data[iso_year] = {}
        
        archive_data[iso_year][week_num] = archive_data[iso_year].get(week_num, 0) + 1
            
    # Преобразуем в отсортированный список для шаблона
    final_archive = []
    sorted_years = sorted(archive_data.keys(), reverse=True)
    
    for y in sorted_years:
        weeks = []
        sorted_weeks = sorted(archive_data[y].keys(), reverse=True)
        for wn in sorted_weeks:
            weeks.append({
                'number': wn,
                'count': archive_data[y][wn]
            })
        final_archive.append({
            'year': y,
            'weeks': weeks
        })

    context = {
        'archive': final_archive,
        'profile': profile,
    }
    return render(request, 'fitness/workout_archive.html', context)

@login_required
def api_get_workouts_by_week(request, year, week):
    """
    API для получения тренировок за конкретный ISO-год и неделю.
    """
    from datetime import datetime, timedelta
    
    # ISO week start (Monday) - %G is ISO Year, %V is ISO Week, %u is Day of Week (1-7)
    d = f"{year}-W{week:02d}-1"
    try:
        monday = datetime.strptime(d, "%G-W%V-%u").date()
    except ValueError:
        # Fallback for weird edge cases
        monday = datetime.strptime(f"{year}-01-01", "%Y-%m-%d").date()
        
    sunday = monday + timedelta(days=6)
    
    workouts = Workout.objects.filter(
        user=request.user, 
        date__range=[monday, sunday]
    ).prefetch_related('sets', 'cardio_entries').order_by('-date')
    
    data = []
    months_ru = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    for w in workouts:
        data.append({
            'id': w.id,
            'date_formatted': f"{w.date.day} {months_ru.get(w.date.month)} {w.date.year}",
            'date_raw': w.date.strftime('%Y-%m-%d'),
            'sets_count': w.sets.count(),
            'has_cardio': w.cardio_entries.exists(),
            'total_volume': float(w.total_volume),
            'total_cardio_min': w.total_cardio_minutes,
            'url': f"/workout/{w.id}/"
        })
        
    return JsonResponse({'workouts': data})
