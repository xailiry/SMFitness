import subprocess
import sys

def run_cmd(args, log_file):
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"COMMAND: {' '.join(args)}\n")
            f.write(f"STDOUT:\n{result.stdout}\n")
            f.write(f"STDERR:\n{result.stderr}\n")
            f.write(f"RETURN CODE: {result.returncode}\n")
        return result.returncode == 0
    except Exception as e:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(str(e))
        return False

print("Creating migrations...")
if run_cmd([r'venv\Scripts\python.exe', 'manage.py', 'makemigrations'], 'makemigrations_log.txt'):
    print("Applying migrations...")
    if run_cmd([r'venv\Scripts\python.exe', 'manage.py', 'migrate'], 'migrate_final_log.txt'):
        print("SUCCESS")
    else:
        print("MIGRATE FAILED")
else:
    print("MAKEMIGRATIONS FAILED")
