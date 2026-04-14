from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from rest_framework.response import Response
from rest_framework import status
import logging
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from apps.transactions.serializers.withdrawal_service import WithdrawalService
from apps.core.permissions import IsVerified

logger = logging.getLogger(__name__)


class WithdrawAPIView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    @extend_schema(
        request=inline_serializer(
            name="WithdrawRequest",
            fields={
                "amount": serializers.DecimalField(max_digits=10, decimal_places=2)
            },
        ),
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT),
            400: OpenApiResponse(response=OpenApiTypes.OBJECT),
        },
    )
    def post(self, request):
        amount = Decimal(request.data.get("amount", 0))

        try:
            tx = WithdrawalService.process_withdrawal(request.user, amount)

            data = tx.metadata_info

            return Response(
                {
                    "success": True,
                    "message": "Withdrawal initiated successfully",
                    "transaction_id": str(tx.id),
                    "withdrawal_id": tx.transaction_identifier,
                    "status": tx.status,
                    "requested_amount": float(data.get("initial_amount", 0)),
                    "system_cut": float(data.get("system_cut", 0)),
                    "intasend_fee": float(data.get("intasend_fee", 0)),
                    "payout_amount": float(data.get("payout_amount", 0)),
                    "total_system_wallet_credit": float(
                        data.get("system_cut", 0) + data.get("intasend_fee", 0)
                    ),
                    "intasend_total_deduction": float(
                        data.get("payout_amount", 0) + data.get("intasend_fee", 0)
                    ),
                    "payout_response": data.get("payout_response", {}),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Withdrawal failed for {request.user.email}: {e}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
