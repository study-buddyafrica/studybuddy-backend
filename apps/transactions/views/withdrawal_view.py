from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from rest_framework.response import Response
from rest_framework import status
import logging
from apps.transactions.serializers.withdrawal_service import WithdrawalService

logger = logging.getLogger(__name__)
class WithdrawAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = Decimal(request.data.get("amount", 0))
        
        try:
            tx = WithdrawalService.process_withdrawal(request.user, amount)
            return Response({
                "success": True, 
                "message": "Withdrawal initiated successfully",
                "transaction_id": str(tx.id),
                "withdrawal_id": tx.transaction_identifier,
                "amount": float(tx.amount.amount),
                "status": tx.status,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Withdrawal failed for {request.user.email}: {e}")
            return Response({
                "success": False, 
                "error": str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

class TestB2CPayoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Test B2C payout with current user"""
        result = WithdrawalService.test_b2c_payout(request.user)
        return Response(result)

class CheckIntaSendBalanceView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Check IntaSend account balance"""
        result = WithdrawalService.check_intasend_balance()
        return Response(result)