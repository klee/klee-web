from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Creates/Updates an Admin user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            action='store',
            dest='username',
            default=None,
            help='Admin username'
        )

        parser.add_argument(
            '--password',
            action='store',
            dest='password',
            default=None,
            help='Admin password'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        password = options.get('password')
        if not username or not password:
            raise CommandError('You must specify a username and password')
        user, created = get_user_model() \
            .objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print('{0} updated'.format(username))
