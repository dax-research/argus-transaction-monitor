from django.core.management.base import BaseCommand
from django.db import connection
from transactions.models import Transaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Fix transactions with invalid decimal amounts'

    def handle(self, *args, **options):
        """
        This command identifies and fixes transactions with invalid decimal values
        that cause SQLite conversion errors in the admin interface.
        """
        # Use raw SQL to check for problematic records
        with connection.cursor() as cursor:
            # Look for NULL or empty amounts
            cursor.execute(
                "SELECT id, txn_id, amount FROM transactions_transaction WHERE amount IS NULL OR amount = ''"
            )
            problematic_records = cursor.fetchall()
            
            if problematic_records:
                self.stdout.write(
                    self.style.WARNING(
                        f"\nFound {len(problematic_records)} transactions with invalid amounts:"
                    )
                )
                for record in problematic_records:
                    self.stdout.write(f"  ID: {record[0]}, TXN_ID: {record[1]}, Amount: {record[2]}")
                
                # Delete the problematic records
                cursor.execute(
                    "DELETE FROM transactions_transaction WHERE amount IS NULL OR amount = ''"
                )
                self.stdout.write(
                    self.style.SUCCESS(f"\nDeleted {cursor.rowcount} transactions with invalid amounts")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("No transactions with invalid amounts found")
                )
        
        # Verify the fix
        transaction_count = Transaction.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"\nTotal transactions in database: {transaction_count}")
        )
