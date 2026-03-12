from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from .models import Workout, WorkoutSet, CardioEntry, UserProfile, Exercise, CARDIO_CHOICES
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


class WorkoutForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-gray-800 dark:text-gray-200',
            }
        ),
        initial=timezone.now().date,
        label='Дата тренировки'
    )

    class Meta:
        model = Workout
        fields = ['date', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-5 py-4 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all resize-none min-h-[100px] text-gray-800 dark:text-gray-200',
                'placeholder': 'Как прошло занятие? Какое было самочувствие?',
                'rows': 3,
            }),
        }


class WorkoutSetForm(forms.ModelForm):
    class Meta:
        model = WorkoutSet
        fields = ['exercise', 'sets', 'reps', 'weight', 'is_bodyweight']
        widgets = {
            'exercise': forms.Select(attrs={'class': 'w-full p-2 border rounded dark:bg-dark-700 dark:border-gray-600 dark:text-gray-200'}),
            'sets': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded dark:bg-dark-700 dark:border-gray-600 dark:text-gray-200', 'min': 1, 'placeholder': '3'}),
            'reps': forms.TextInput(attrs={'class': 'w-full p-2 border rounded dark:bg-dark-700 dark:border-gray-600 dark:text-gray-200', 'placeholder': '10 или 12-10-8-6'}),
            'weight': forms.TextInput(attrs={'class': 'w-full p-2 border rounded dark:bg-dark-700 dark:border-gray-600 dark:text-gray-200', 'placeholder': '50 или 50-52.5-55'}),
            'is_bodyweight': forms.CheckboxInput(attrs={'class': 'peer w-4 h-4 text-brand-600 border-gray-300 dark:border-gray-600 rounded focus:ring-brand-500 cursor-pointer mt-1'}),
        }

    reps = forms.CharField(
        validators=[RegexValidator(r'^[0-9.,\- ]+$', "Разрешены только числа, точки, запятые, тире и пробелы.")],
        widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded dark:bg-dark-700 dark:border-gray-600 dark:text-gray-200', 'placeholder': '10 или 12-10-8-6'})
    )
    weight = forms.CharField(
        required=False,
        validators=[RegexValidator(r'^[0-9.,\- ]+$', "Разрешены только числа, точки, запятые, тире и пробелы.")],
        widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded dark:bg-dark-700 dark:border-gray-600 dark:text-gray-200', 'placeholder': '50 или 50-52.5-55'})
    )

    def __init__(self, *args, **kwargs):
        super(WorkoutSetForm, self).__init__(*args, **kwargs)
        self.fields['weight'].required = False
        self.fields['exercise'].queryset = Exercise.objects.exclude(muscle_group='cardio')

    def clean(self):
        cleaned_data = super().clean()
        sets = cleaned_data.get('sets')
        reps = cleaned_data.get('reps')
        weight = cleaned_data.get('weight')
        is_bodyweight = cleaned_data.get('is_bodyweight')
        
        if sets:
            if sets > 50:
                self.add_error('sets', "Количество подходов не может превышать 50.")
            
            if reps:
                reps_str = str(reps).replace(',', '-').replace(' ', '-')
                reps_parts = [r.strip() for r in reps_str.split('-') if r.strip()]
                
                # Validate all items are numbers
                for r in reps_parts:
                    if not r.isdigit():
                        self.add_error('reps', f"Значение '{r}' должно быть целым числом.")
                    else:
                        val = int(r)
                        if val > 1000:
                            self.add_error('reps', f"Количество повторений ({val}) слишком велико. Максимум 1000.")
                        elif val < 1:
                            self.add_error('reps', f"Количество повторений должно быть не менее 1.")

                # If user provided a series of numbers, length must match `sets`.
                if len(reps_parts) > 1 and len(reps_parts) != sets:
                    self.add_error('reps', f"Указано {len(reps_parts)} значений повторений для {sets} подходов. Количество должно совпадать.")
            
            if weight and not is_bodyweight:
                w_str = str(weight).replace(',', '-').replace(' ', '-')
                w_parts = [w.strip() for w in w_str.split('-') if w.strip()]
                
                # Validate all items are numbers
                for w in w_parts:
                    try:
                        val = float(w)
                        if val > 1000:
                            self.add_error('weight', f"Вес ({val} кг) слишком велик. Максимум 1000 кг.")
                        elif val < 0:
                            self.add_error('weight', f"Вес не может быть отрицательным.")
                    except ValueError:
                        self.add_error('weight', f"Значение '{w}' должно быть числом.")

                if len(w_parts) > 1 and len(w_parts) != sets:
                    self.add_error('weight', f"Указано {len(w_parts)} значений веса для {sets} подходов. Количество должно совпадать.")
                
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['height', 'current_weight', 'target_weight', 'goal', 'avatar']
        widgets = {
            'height': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-gray-800 dark:text-gray-200',
                'placeholder': '175',
                'min': 100,
                'max': 250,
            }),
            'current_weight': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-gray-800 dark:text-gray-200',
                'placeholder': '70.0',
                'step': '0.1',
                'min': 30,
            }),
            'target_weight': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-gray-800 dark:text-gray-200',
                'placeholder': '65.0',
                'step': '0.1',
                'min': 30,
            }),
            'goal': forms.Select(attrs={
                'class': 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-gray-800 dark:text-gray-200',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'avatar-input',
                'accept': 'image/*',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'goal' in self.fields:
            # Remove the '---------' empty choice
            self.fields['goal'].choices = [c for c in self.fields['goal'].choices if c[0]]


class AvatarUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'avatar-input',
                'accept': 'image/*',
            }),
        }


INPUT_CLS = 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-3 py-2.5 outline-none focus:border-brand-500 text-gray-800 dark:text-gray-200 font-medium text-sm transition-all'

class CardioEntryForm(forms.ModelForm):
    activity = forms.ChoiceField(
        choices=[('', '-- Выберите --')] + CARDIO_CHOICES,
        widget=forms.Select(attrs={'class': INPUT_CLS}),
        label="Активность",
        required=True
    )
    
    distance_km = forms.DecimalField(
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLS, 'min': 0, 'max': 1000, 'step': '0.01', 'placeholder': '5.00',
        }),
        label='Дистанция (км)',
    )

    class Meta:
        model = CardioEntry
        fields = ['activity', 'duration_minutes', 'distance_km', 'avg_heart_rate', 'calories_burned']
        widgets = {
            'duration_minutes': forms.NumberInput(attrs={
                'class': INPUT_CLS, 'min': 1, 'max': 1440, 'placeholder': '30',
            }),
            'avg_heart_rate': forms.NumberInput(attrs={
                'class': INPUT_CLS, 'min': 40, 'max': 220, 'placeholder': '155',
            }),
            'calories_burned': forms.NumberInput(attrs={
                'class': INPUT_CLS, 'min': 0, 'max': 10000, 'placeholder': '300',
            }),
        }
        error_messages = {
            'duration_minutes': {
                'required': 'Необходимо указать длительность кардио',
            }
        }
class UsernameUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-gray-800 dark:text-gray-200 font-bold',
            }),
        }
        labels = {
            'username': 'Имя пользователя',
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-gray-800 dark:text-gray-200',
            })

    def clean_new_password1(self):
        new_password = self.cleaned_data.get("new_password1")
        old_password = self.cleaned_data.get("old_password")
        if new_password and old_password and new_password == old_password:
            raise forms.ValidationError(
                "Новый пароль не может совпадать со старым.",
                code='password_identical',
            )
        return new_password
