from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from djmoney.money import Money

from apps.transactions.models import Wallet, Transaction
from apps.transactions.services import process_session_payment

from .models import Wallet, Transaction
from .services import process_session_payment

User = get_user_model()

class WalletRoutingEngineTests(TestCase):
    def setUp(self):
        """
        Set up the isolated test environment with a Student, Teacher, and System wallet.
        """
        # 1. Create the System Admin (Wallet is auto-created by signals)
        self.admin_user = User.objects.create_superuser(
            username='system_admin', 
            email='admin@vyron.com', 
            password='password123',
            first_name='System',
            last_name='Admin'
        )
        # Fetch the auto-created wallet and update it
        self.system_wallet = self.admin_user.wallet
        self.system_wallet.account_type = 'system'
        self.system_wallet.balance = Money(0, 'KES')
        self.system_wallet.save()

        # 2. Create the Student
        self.student_user = User.objects.create_user(
            username='student_mike', 
            email='mike@example.com', 
            password='password123',
            first_name='Mike',
            last_name='Student'
        )
        # Fetch and update the student's auto-created wallet
        self.student_wallet = self.student_user.wallet
        self.student_wallet.account_type = 'student'
        self.student_wallet.balance = Money(2000.00, 'KES')
        self.student_wallet.save()

        # 3. Create the Teacher
        self.teacher_user = User.objects.create_user(
            username='teacher_jane', 
            email='jane@example.com', 
            password='password123',
            first_name='Jane',
            last_name='Teacher'
        )
        # Fetch and update the teacher's auto-created wallet
        self.teacher_wallet = self.teacher_user.wallet
        self.teacher_wallet.account_type = 'teacher'
        self.teacher_wallet.balance = Money(0, 'KES')
        self.teacher_wallet.save()
    def test_process_session_payment_70_30_split(self):
        """
        Test that a 1000 KES payment is accurately split: 
        700 to Teacher, 300 to System, and deducted from Student.
        """
        payment_amount = Money(1000.00, 'KES')

        # Execute the service
        success = process_session_payment(
            payment_amount=payment_amount,
            student_wallet=self.student_wallet,
            teacher_wallet=self.teacher_wallet
        )

        self.assertTrue(success)

        # Refresh wallets from the test database to get updated balances
        self.student_wallet.refresh_from_db()
        self.teacher_wallet.refresh_from_db()
        self.system_wallet.refresh_from_db()

        # --- FINANCIAL ASSERTIONS ---
        # Student should have 1000 KES left (2000 - 1000)
        self.assertEqual(self.student_wallet.balance, Money(1000.00, 'KES'))
        
        # Teacher should have exactly 70% (700 KES)
        self.assertEqual(self.teacher_wallet.balance, Money(700.00, 'KES'))
        
        # System should have exactly 30% (300 KES)
        self.assertEqual(self.system_wallet.balance, Money(300.00, 'KES'))

    def test_process_session_payment_insufficient_funds(self):
        """
        Test that the engine safely blocks transactions if the student is broke.
        """
        # Try to pay 5000 KES when the student only has 2000 KES
        massive_payment = Money(5000.00, 'KES')

        # Your custom withdraw() method raises a ValueError on insufficient funds
        with self.assertRaises(ValueError):
            process_session_payment(
                payment_amount=massive_payment,
                student_wallet=self.student_wallet,
                teacher_wallet=self.teacher_wallet
            )

        # Ensure NO money was moved (Database rollback verification)
        self.student_wallet.refresh_from_db()
        self.teacher_wallet.refresh_from_db()
        self.system_wallet.refresh_from_db()

        self.assertEqual(self.student_wallet.balance, Money(2000.00, 'KES'))
        self.assertEqual(self.teacher_wallet.balance, Money(0, 'KES'))

    def test_transaction_audit_logs_created(self):
        """
        Verify that the routing engine accurately creates the 3 transaction receipts.
        """
        payment_amount = Money(1000.00, 'KES')
        process_session_payment(payment_amount, self.student_wallet, self.teacher_wallet)

        # There should be exactly 3 transactions logged in the database
        self.assertEqual(Transaction.objects.count(), 3)

        student_tx = Transaction.objects.get(wallet=self.student_wallet)
        teacher_tx = Transaction.objects.get(wallet=self.teacher_wallet)
        system_tx = Transaction.objects.get(wallet=self.system_wallet)

        # Check amounts recorded in the logs
        self.assertEqual(student_tx.amount, Money(1000.00, 'KES'))
        self.assertEqual(teacher_tx.amount, Money(700.00, 'KES'))
        self.assertEqual(system_tx.amount, Money(300.00, 'KES'))