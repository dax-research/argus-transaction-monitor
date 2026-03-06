"""
users/management/commands/seed_oauth_app.py

Creates (or updates) the Argus Frontend OAuth2 Application record so that
the Resource Owner Password Credentials grant works out of the box.

Usage:
    python manage.py seed_oauth_app
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User as DjangoUser


class Command(BaseCommand):
    help = "Create the Argus Frontend OAuth2 Application (public ROPC client)."

    def handle(self, *args, **options):
        # Import here so the command doesn't break if oauth2_provider isn't
        # installed yet (e.g. before the first migration).
        from oauth2_provider.models import Application

        CLIENT_ID = "argus-frontend-client"

        # Use the first superuser as owner, or None
        owner = DjangoUser.objects.filter(is_superuser=True).first()

        app, created = Application.objects.update_or_create(
            client_id=CLIENT_ID,
            defaults={
                "name":                    "Argus Frontend",
                "client_type":             Application.CLIENT_PUBLIC,
                "authorization_grant_type": Application.GRANT_PASSWORD,
                "client_secret":           "",   # public client — no secret in JS
                "user":                    owner,
                "skip_authorization":      True,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} OAuth2 Application: client_id={CLIENT_ID!r}  pk={app.pk}"
            )
        )
