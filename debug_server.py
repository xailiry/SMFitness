import subprocess
import time
import os

log_file = os.path.abspath('runserver_debug.txt')
with open(log_file, 'w') as f:
    f.write("Starting server debug...\n")

try:
    # Запускаем сервер и ждем несколько секунд, чтобы он успел выдать ошибку или запуститься
    process = subprocess.Popen(
        [r'venv\Scripts\python.exe', 'manage.py', 'runserver', '--noreload'],
        stdout=open(log_file, 'a'),
        stderr=subprocess.STDOUT,
        text=True
    )
    time.sleep(10) # Даем время на запуск или падение
    if process.poll() is not None:
        with open(log_file, 'a') as f:
            f.write(f"\nProcess exited with code: {process.returncode}\n")
    else:
        with open(log_file, 'a') as f:
            f.write("\nProcess is still running.\n")
        process.terminate()
except Exception as e:
    with open(log_file, 'a') as f:
        f.write(f"\nException: {str(e)}\n")

print("DEBUG DONE")
