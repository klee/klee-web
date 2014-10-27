from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from optparse import make_option


class Command(BaseCommand):
    help = 'Creates/Updates an Admin user'

    username_option = make_option(
        '--username',
        action='store',
        dest='username',
        default=None,
        help='Admin username'
    )

    password_option = make_option(
        '--password',
        action='store',
        dest='password',
        default=None,
        help='Admin password'
    )

    option_list = BaseCommand.option_list + (username_option, password_option)

    def handle(self, *args, **options):
        username = options.get('username')
        password = options.get('password')
        if not username or not password:
            raise StandardError('You must specify a username and password')
        user, created = get_user_model() \
            .objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print('{0} updated'.format(username))
