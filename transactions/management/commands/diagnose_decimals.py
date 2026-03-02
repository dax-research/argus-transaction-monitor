from django.core.management.base import BaseCommand
from django.db import connection
from decimal import Decimal, InvalidOperation


class Command(BaseCommand):
    help = 'Diagnose transactions with invalid decimal amounts'

    def handle(self, *args, **options):
        """
        This command diagnoses which transactions have amounts that
        fail to convert to Decimal values.
        """
        with connection.cursor() as cursor:
            # Get all amounts as raw values
            cursor.execute(
                "SELECT id, txn_id, amount, typeof(amount) FROM transactions_transaction"
            )
            records = cursor.fetchall()
            
            self.stdout.write(f"\nTotal transactions: {len(records)}\n")
            
            problematic = []
            for record_id, txn_id, amount, type_name in records:
                self.stdout.write(f"ID: {record_id}, TXN: {txn_id}, Amount: {repr(amount)}, Type: {type_name}")
                
                # Try to convert to Decimal
                try:
                    if amount is not None:
                        dec_val = Decimal(str(amount))
                    self.stdout.write(f"  ✓ Valid: {dec_val if amount is not None else 'NULL'}")
                except (InvalidOperation, ValueError, TypeError) as e:
                    self.stdout.write(f"  ✗ Invalid: {e}")
                    problematic.append((record_id, txn_id, amount))
            
            if problematic:
                self.stdout.write(self.style.ERROR(f"\n\nFound {len(problematic)} problematic records:"))
                for record_id, txn_id, amount in problematic:
                    self.stdout.write(f"  ID: {record_id}, TXN: {txn_id}, Amount: {repr(amount)}")
            else:
                self.stdout.write(self.style.SUCCESS("\n\nAll amounts are valid!"))
