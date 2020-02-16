from django.core.management.commands.runserver import BaseRunserverCommand
import platform
import os
from django.conf import settings


class Command(BaseRunserverCommand):
    def inner_run(self, *args, **options):
        env = platform.system()
        if env == 'Linux':
            os.system('memcached -m 128 -d')
        if env == 'Windows':
            path = os.path.join(settings.BASE_DIR, 'memcached')
            os.chdir(path)
            os.system(f"memcached.exe -m 128 -d")
        super(Command, self).inner_run(*args, **options)
