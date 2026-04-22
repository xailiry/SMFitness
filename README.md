<div align="center">

# ⚡ SMFitness

**Персональный фитнес-ежедневник с интеграцией ИИ**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-smfitness.onrender.com-2563EB?style=for-the-badge&logo=googlechrome&logoColor=white)](https://smfitness.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)

</div>

---

## О проекте

SMFitness — бесплатное веб-приложение для самостоятельно тренирующихся. Ведёте тренировочный дневник, смотрите графики прогресса и получаете персональные рекомендации от ИИ — всё в одном месте, без подписок и рекламы.

Приложение доступно онлайн по адресу **[smfitness.onrender.com](https://smfitness.onrender.com)** и корректно работает на десктопе и мобильных устройствах.

---

## Возможности

### 🏋️ Журнал тренировок
- Силовые тренировки: выбор упражнений из базы **80+ позиций** с группировкой по мышцам
- Гибкий формат повторений — например `10-8-6` или `50-52.5-55`
- Кардио: тип активности, длительность, дистанция, пульс, калории
- Сохранение тренировок как **шаблоны** для повторного использования
- Заметки и фиксация веса тела на дату тренировки

### 📊 Дашборд и аналитика
- Виджеты статистики: общий объём в тоннах, серия недель (стрик), личные рекорды
- Интерактивные **графики прогресса** по каждому упражнению (Chart.js)
- Карусель «Инсайты недели» — автоматические подсказки на основе ваших данных
- Виджет **цели**: прогресс до целевого веса + прогноз даты по линейной регрессии
- Расчёт **ИМТ** с цветовой индикацией нормы
- Страница продвинутой аналитики со сводными таблицами объёмов

### 🤖 ИИ-сервисы (Google Gemini)
- **Советы ИИ** — анализ ваших тренировок за 30 дней, персональные текстовые рекомендации
- **Стратегия ИИ** — план питания с расчётом КБЖУ и тренировочная программа на неделю

### 🔐 Прочее
- Система регистрации, авторизации и профиля с onboarding-анкетой
- Тёмная тема с защитой от белой вспышки при загрузке
- Адаптивный интерфейс для десктопа и мобильных

---

## Стек технологий

| Слой | Технология |
|------|-----------|
| Backend | Python 3.12, Django 5.x |
| База данных | SQLite (dev) / PostgreSQL (prod) |
| Frontend | HTML, Tailwind CSS, Vanilla JS |
| Графики | Chart.js |
| ИИ | Google Gemini API |
| Хостинг | Render.com |

---

## Быстрый старт (локально)

### 1. Клонировать репозиторий

```bash
git clone https://github.com/xailiry/SMFitness.git
cd SMFitness
```

### 2. Создать `.env` файл

```env
SECRET_KEY=любая_длинная_случайная_строка
DEBUG=True
GEMINI_API_KEY=ваш_ключ_от_google_ai_studio
```

> Получить ключ Gemini API бесплатно: [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 3. Установить зависимости и запустить

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

Приложение откроется на `http://127.0.0.1:8000/`

---

## Структура проекта

```
SMFitness/
├── fitness/
│   ├── models.py        # Модели БД (Workout, Exercise, UserProfile и др.)
│   ├── views.py         # Вся бизнес-логика
│   ├── utils.py         # Расчёт КБЖУ, линейная регрессия, стрики
│   └── templates/       # HTML-шаблоны
├── static/
│   └── js/
│       └── fitness_charts.js  # Логика графиков Chart.js
├── SMFitness/
│   └── settings.py      # Настройки Django
├── requirements.txt
└── manage.py
```

---

<div align="center">

Сделано в рамках индивидуального проекта · 10 класс · 2025 / 2026

</div>
