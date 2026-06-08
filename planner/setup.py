import os
import sys
import django
from django.conf import settings as django_settings


def initialize():
    """Configure and set up Django for standalone use. Safe to call multiple times."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'planner.settings')

    if not django_settings.configured:
        django.setup()
        _run_migrations()
        return

    from django.apps import apps
    if not apps.ready:
        django.setup()
        _run_migrations()


def _run_migrations():
    from django.core.management import call_command
    call_command('migrate', '--run-syncdb', verbosity=0)
