import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
    from django.core.management import call_command
    call_command('check')
    print('SUCCESS')
except Exception as e:
    import traceback
    with open('error_log.txt', 'w') as f:
        traceback.print_exc(file=f)
    print('ERROR WRITTEN')
