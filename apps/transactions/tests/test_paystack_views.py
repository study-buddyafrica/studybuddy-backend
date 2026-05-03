from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from djmoney.money import Money
from rest_framework import status
from rest_framework.test import APITestCase

from apps.transactions.models import Transaction, Wallet
from apps.users.models import TeacherProfile

User = get_user_model()


class PaystackDepositViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student-paystack@example.com",
            first_name="Test",
            last_name="Student",
            username="student-paystack",
            password="StrongPass123",
        )
        self.user.account_confirmed = True
        self.user.save(update_fields=["account_confirmed"])
        self.client.force_authenticate(self.user)

    def test_deposit_view_initiates_paystack_checkout(self):
        fake_result = {
            "checkout_url": "https://checkout.paystack.com/abc123",
            "transaction_id": "tx-123",
            "reference": "SB_abc123",
        }

        with patch(
            "apps.transactions.views.deposit_view.PaymentService.initiate_checkout",
            return_value=fake_result,
        ) as mock_checkout:
            response = self.client.post(
                "/api/transactions/wallet/deposit/",
                {"amount": "1500"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["checkout_url"], fake_result["checkout_url"])
        self.assertEqual(response.data["reference"], fake_result["reference"])
        mock_checkout.assert_called_once()


class PaystackWithdrawalViewTests(APITestCase):
    def setUp(self):
        self.system_user = User.objects.create_superuser(
            email="system@example.com",
            first_name="System",
            last_name="Admin",
            username="system-admin",
            password="StrongPass123",
        )
        self.system_user.account_confirmed = True
        self.system_user.save(update_fields=["account_confirmed"])
        self.system_wallet = self.system_user.wallet
        self.system_wallet.account_type = "system"
        self.system_wallet.balance = Money(0, "KES")
        self.system_wallet.save(update_fields=["account_type", "balance"])

        self.teacher_user = User.objects.create_user(
            email="teacher-paystack@example.com",
            first_name="Grace",
            last_name="Otieno",
            username="teacher-paystack",
            password="StrongPass123",
            role="teacher",
        )
        self.teacher_user.account_confirmed = True
        self.teacher_user.save(update_fields=["account_confirmed"])
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            phone="+254700000000",
            hourly_rate=Money(1500, "KES"),
            profile_picture=SimpleUploadedFile(
                "profile.jpg", b"fake-image-data", content_type="image/jpeg"
            ),
            paystack_recipient_code="RCP_test_123",
            is_verified=True,
        )
        self.teacher_wallet = self.teacher_user.wallet
        self.teacher_wallet.balance = Money(2500, "KES")
        self.teacher_wallet.save(update_fields=["balance"])
        self.client.force_authenticate(self.teacher_user)

    def test_withdrawal_view_initiates_paystack_transfer(self):
        fake_response = {
            "status": True,
            "message": "Transfer queued",
            "data": {"transfer_code": "TRF_test_123"},
        }

        with patch(
            "apps.transactions.serializers.withdrawal_service.requests.post"
        ) as mock_post:
            mock_post.return_value = MagicMock(json=lambda: fake_response)

            response = self.client.post(
                "/api/withdraw/",
                {"amount": "1000"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["payment_gateway"], "paystack")
        self.assertIn("payout_response", response.data)

        tx = Transaction.objects.get(transaction_identifier__startswith="withdraw_")
        self.assertEqual(tx.payment_method, "paystack")
        self.assertEqual(tx.status, "processing")
        self.assertEqual(tx.metadata_info["transfer_code"], "TRF_test_123")
        self.system_user.wallet.refresh_from_db()
        self.teacher_user.wallet.refresh_from_db()
        self.assertEqual(self.system_user.wallet.balance, Money(300, "KES"))
        self.assertEqual(self.teacher_user.wallet.balance, Money(1500, "KES"))
