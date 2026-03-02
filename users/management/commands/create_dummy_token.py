from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from rest_framework.authtoken.models import Token

from users.models import User as CustomUser


class Command(BaseCommand):
    help = "Create a Django auth user, matching custom users.User, and create a Token with a specific key"

    def add_arguments(self, parser):
        parser.add_argument('--token', type=str, help='Token key to create', required=True)
        parser.add_argument('--user-id', type=str, help='User ID (matches custom users.User.user_id)', required=True)
        parser.add_argument('--password', type=str, help='Password for the Django auth user', required=False)

    def handle(self, *args, **options):
        token_key = options['token']
        user_id = options['user_id']
        password = options.get('password') or get_random_string(12)

        UserModel = get_user_model()

        # Create or get Django auth user
        auth_user, created = UserModel.objects.get_or_create(username=user_id)
        if created:
            auth_user.set_password(password)
            auth_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created auth user: {user_id}'))
        else:
            # ensure password set if requested
            if options.get('password'):
                auth_user.set_password(password)
                auth_user.save()
                self.stdout.write(self.style.SUCCESS(f'Updated password for auth user: {user_id}'))
            else:
                self.stdout.write(self.style.NOTICE(f'Auth user already exists: {user_id}'))

        # Create or get custom users.User
        custom_user, cu_created = CustomUser.objects.get_or_create(user_id=user_id, defaults={'phone': '', 'account_balance': 0.0})
        if cu_created:
            self.stdout.write(self.style.SUCCESS(f'Created custom users.User: {user_id}'))
        else:
            self.stdout.write(self.style.NOTICE(f'Custom users.User already exists: {user_id}'))

        # Create Token with provided key
        token_obj = None
        existing = Token.objects.filter(key=token_key).first()
        if existing:
            # reassign to our auth user
            existing.user = auth_user
            existing.save()
            token_obj = existing
            self.stdout.write(self.style.WARNING(f'Token already existed; reassigned to user {user_id}'))
        else:
            token_obj = Token.objects.create(user=auth_user, key=token_key)
            self.stdout.write(self.style.SUCCESS(f'Created token for user {user_id}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Done.'))
        self.stdout.write(f'Auth username: {auth_user.username}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'Token: {token_obj.key}')
