import uuid
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from djmoney.money import Money
from django.conf import settings
from apps.transactions.models import Transaction, Wallet
from intasend import APIService
import json

logger = logging.getLogger(__name__)

class WithdrawalService:
    @staticmethod
    @transaction.atomic
    def process_withdrawal(user, amount: Decimal):
        """
        Process withdrawal using IntaSend M-Pesa transfer API
        """
        try:
            wallet = Wallet.objects.select_for_update().get(user=user)
            amount_money = Money(amount, 'KES')

            # Validate amount
            if amount <= 0:
                raise ValueError("Withdrawal amount must be greater than 0.")

            if wallet.balance < amount_money:
                wallet.failed_withdraw_attempts += 1
                wallet.save(update_fields=['failed_withdraw_attempts'])
                
                if wallet.failed_withdraw_attempts >= 3:
                    user.is_active = False
                    user.save(update_fields=['is_active'])
                raise ValueError("Insufficient balance for withdrawal.")

            # Calculate distribution (30% system cut)
            system_cut = amount_money * Decimal("0.30")
            payout_amount = amount_money - system_cut

            # Validate minimum payout amount (IntaSend minimum is usually 10 KES)
            if payout_amount.amount < 10:
                raise ValueError("Payout amount too small. Minimum withdrawal is 15 KES.")

            # Deduct from user wallet
            wallet.balance -= amount_money
            wallet.failed_withdraw_attempts = 0
            wallet.save()

            # Credit system wallet
            system_wallet = Wallet.objects.select_for_update().get(user__is_superuser=True)
            system_wallet.balance += system_cut
            system_wallet.save()

            # Generate unique transaction identifier
            transaction_identifier = f"withdraw_{user.id}_{uuid.uuid4().hex[:12]}"

            # Create transaction record
            tx = Transaction.objects.create(
                wallet=wallet,
                transaction_identifier=transaction_identifier,
                transaction_type="withdrawal",
                amount=amount_money,
                payment_method="intasend",
                status="success",
                description=f"Withdrawal: {amount_money} (System: {system_cut}, Payout: {payout_amount})",
                metadata_info={
                    "system_cut": float(system_cut.amount),
                    "payout_amount": float(payout_amount.amount),
                    "initiator": str(user.email),
                    "user_id": str(user.id),
                    "withdrawal_type": "teacher_payout",
                    "calculated_at": str(timezone.now()),
                }
            )

            # Send payout via IntaSend M-Pesa transfer
            try:
                payout_response = WithdrawalService._send_intasend_mpesa_transfer(user, payout_amount, tx)
                tx.metadata_info.update({
                    "payout_response": payout_response,
                    "payout_id": payout_response.get("id", ""),
                    "invoice_id": payout_response.get("invoice_id", ""),
                    "withdrawal_status": payout_response.get("state", "PROCESSING"),
                })
                tx.status = "processing"
                tx.save()
                
                logger.info(f"Withdrawal initiated for {user.email}: {amount_money}")
                
            except Exception as e:
                # If payout fails, refund the wallet
                wallet.balance += amount_money
                wallet.save()
                
                system_wallet.balance -= system_cut
                system_wallet.save()
                
                tx.status = "failed"
                tx.metadata_info["payout_error"] = str(e)
                tx.metadata_info["refunded"] = True
                tx.save()
                
                logger.error(f"Withdrawal failed for {user.email}: {e}")
                raise e

            return tx

        except Wallet.DoesNotExist:
            raise ValueError("Wallet not found for user.")
        except Exception as e:
            logger.error(f"Withdrawal processing error for {user.email}: {e}")
            raise

    @staticmethod
    def _send_intasend_mpesa_transfer(user, payout_amount: Money, tx: Transaction):
        """
        Send M-Pesa transfer using IntaSend SDK transfer.mpesa() method.
        """
        try:
            # Get user's M-Pesa number
            mpesa_number ="254745897362"
            if not mpesa_number:
                raise ValueError("User M-Pesa number not found. Please update your profile with a valid phone number.")
            
            # Format M-Pesa number (remove + if present)
            formatted_number = WithdrawalService._format_phone_number(mpesa_number)
            logger.info(f"Using M-Pesa number: {formatted_number}")

            # Initialize IntaSend service
            service = APIService(
                token=settings.INTASEND_SECRET_KEY.strip(),
                publishable_key=settings.INTASEND_PUBLISHABLE_KEY.strip(),
                test=True,  # Use test=False for production
            )

            # Prepare transactions list as required by the API
            transactions = [
                {
                    "name":user.username,
                    "account": "254745897362",
                    "amount": float(payout_amount.amount),
                }
            ]

            logger.info(f"Sending M-Pesa transfer: {json.dumps(transactions, indent=2)}")

            # Send M-Pesa transfer using the correct SDK method
            response = service.transfer.mpesa(
                currency="KES",
                transactions=transactions,
                requires_approval="NO"  # Auto-approve the transfer
            )

            logger.info(f"✅ M-Pesa transfer response: {json.dumps(response, indent=2)}")
            
            return response

        except Exception as e:
            logger.error(f"IntaSend M-Pesa transfer failed: {e}")
            raise ValueError(f"Payout service error: {str(e)}")

    @staticmethod
    def _get_user_mpesa_number(user):
        """Safely get and validate user's M-Pesa number"""
        # Try different possible phone number fields
        phone_number = None
        
        # Check user.phone_number (convert to string if it's a number)
        if hasattr(user, 'phone_number') and user.phone:
            phone_number = str(user.phone).strip()
        
        # If no phone number, check other possible fields
        if not phone_number and hasattr(user, 'mobile') and user.mobile:
            phone_number = str(user.mobile).strip()
            
        if not phone_number and hasattr(user, 'phone') and user.phone:
            phone_number = str(user.phone).strip()
            
        # Validate phone number format
        if phone_number:
            # Remove any non-digit characters except +
            import re
            phone_number = re.sub(r'[^\d+]', '', phone_number)
            
            # Basic validation
            if len(phone_number) < 9:
                logger.warning(f"Phone number too short: {phone_number}")
                return None
                
        return phone_number

    @staticmethod
    def _format_phone_number(phone_number):
        """Format phone number to 254 format"""
        # Ensure it's a string
        phone_str = str(phone_number).strip()
        
        # Remove any spaces or special characters except +
        import re
        phone_str = re.sub(r'[^\d+]', '', phone_str)
        
        # Format to 254 format
        if phone_str.startswith('0'):
            return '254' + phone_str[1:]
        elif phone_str.startswith('+'):
            return phone_str[1:]  # Remove + but keep country code
        elif phone_str.startswith('254'):
            return phone_str
        else:
            # Assume it's already in international format without +
            return phone_str

    @staticmethod
    def test_mpesa_transfer(user=None, test_amount=10.0):
        """
        Test IntaSend M-Pesa transfer with a small amount.
        """
        try:
            # Use providFed user or create a test one
            if not user:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.filter(phone__isnull=False).first()
                if not user:
                    return {
                        "success": False,
                        "error": "No user with phone number found for testing"
                    }

            # Test phone number extraction
            mpesa_number ="254745897362"
            formatted_number = WithdrawalService._format_phone_number(mpesa_number) if mpesa_number else None
            
            if not formatted_number:
                return {
                    "success": False,
                    "error": "No valid M-Pesa number found"
                }

            # Initialize IntaSend service
            service = APIService(
                token=settings.INTASEND_SECRET_KEY.strip(),
                publishable_key=settings.INTASEND_PUBLISHABLE_KEY.strip(),
                test=True,
            )

            # Prepare test transaction
            transactions = [
                {
                    "name": user.get_full_name() or user.username,
                    "account": formatted_number,
                    "amount": float(test_amount),
                }
            ]

            logger.info(f"Testing M-Pesa transfer with: {json.dumps(transactions, indent=2)}")
            
            # Send test transfer
            response = service.transfer.mpesa(
                currency="KES",
                transactions=transactions,
                requires_approval="NO"
            )
            
            result = {
                "success": True,
                "user": user.email,
                "phone_number": formatted_number,
                "test_amount": test_amount,
                "response": response,
                "message": "M-Pesa transfer test successful"
            }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "M-Pesa transfer test failed"
            }

    @staticmethod
    def check_intasend_balance():
        """
        Check IntaSend account balance to ensure sufficient funds.
        """
        try:
            service = APIService(
                token=settings.INTASEND_SECRET_KEY.strip(),
                publishable_key=settings.INTASEND_PUBLISHABLE_KEY.strip(),
                test=True,
            )
            
            # Get wallet balance using the SDK
            wallet = service.wallets
            balance_info = wallet.current_balance()
            
            return {
                "success": True,
                "balance": balance_info,
                "message": "Balance retrieved successfully"
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Balance check failed"
            }