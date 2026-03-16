# SMFitness 🏋️‍♂️

> [!NOTE]
> Данный README файл сгенерирован ИИ ( для справки:) )

SMFitness — это веб-приложение для отслеживания тренировок, прогресса веса и анализа активности.

## Как быстро запустить проект локально

### 1. Подготовка (Общее для всех ОС)
Склонируйте репозиторий:
```bash
git clone https://github.com/xailiry/SMFitness.git
cd SMFitness
```

### 2. Настройка окружения
Создайте файл `.env` в корневой папке проекта и добавьте следующие переменные:

```env
# Основные настройки Django
SECRET_KEY=ваш_секретный_ключ (любая длинная случайная строка)
DEBUG=True

# Настройки ИИ (Google Gemini)
# Получить ключ можно здесь: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=ваш_api_ключ_от_gemini

# Настройки безопасности (для продакшена, по умолчанию False)
# SECURE_SSL_REDIRECT=False
# SESSION_COOKIE_SECURE=False
# CSRF_COOKIE_SECURE=False
```

---

### 3. Запуск на Windows (CMD или PowerShell)

1. **Создайте виртуальное окружение:**
   ```bash
   python -m venv venv
   ```
2. **Активируйте окружение:**
   - CMD: `venv\Scripts\activate`
   - PowerShell: `.\venv\Scripts\Activate.ps1`
3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Выполните миграции и запустите сервер:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

---

### 4. Запуск на macOS / Linux (Терминал)

1. **Создайте виртуальное окружение:**
   ```bash
   python3 -m venv venv
   ```
2. **Активируйте окружение:**
   ```bash
   source venv/bin/activate
   ```
3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Выполните миграции и запустите сервер:**
   ```bash
   python3 manage.py migrate
   python3 manage.py runserver
   ```

---

После запуска проект будет доступен по адресу: `http://127.0.0.1:8000/`
