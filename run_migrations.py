import subprocess
import sys

try:
    # Run showmigrations
    result = subprocess.run([r'venv\Scripts\python.exe', 'manage.py', 'showmigrations'], capture_output=True, text=True)
    with open('migrations_check.txt', 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
    print("DONE SHOWMIGRATIONS")
    
    # Run migrate
    result_migrate = subprocess.run([r'venv\Scripts\python.exe', 'manage.py', 'migrate'], capture_output=True, text=True)
    with open('migrate_output.txt', 'w', encoding='utf-8') as f:
        f.write(result_migrate.stdout)
        f.write("\nSTDERR:\n")
        f.write(result_migrate.stderr)
    print("DONE MIGRATE")
except Exception as e:
    with open('migrations_check.txt', 'a', encoding='utf-8') as f:
        f.write("\nEXCEPTION:\n")
        f.write(str(e))
    print("ERROR")
