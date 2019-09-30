#!/usr/bin/env python
import os
import sys

from auth import cognito

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("using settings 'caracal.settings.testing'")
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caracal.settings.testing')
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caracal.settings.development')

    if os.environ['DJANGO_SETTINGS_MODULE'] == 'caracal.settings.testing':
        if input('Do you want to clear testing Cognito users? [y/n] ').lower() in ['y', 'yes']:
            cognito.remove_testing_users()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django.") from exc
    execute_from_command_line(sys.argv)
