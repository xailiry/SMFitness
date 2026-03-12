import subprocess
import sys

try:
    result = subprocess.run([r'venv\Scripts\python.exe', 'manage.py', 'check'], capture_output=True, text=True)
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
        f.write(f"\nReturn Code: {result.returncode}\n")
    print("DONE")
except Exception as e:
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write(str(e))
    print("ERROR")
