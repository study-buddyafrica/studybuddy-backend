from django.shortcuts import render

from apps.transactions.models import Transaction


def deposit_success_view(request):
    """Render a success page after a Paystack redirect without mutating state."""
    reference = (
        request.GET.get("reference")
        or request.GET.get("tracking_id")
        or request.GET.get("checkout_id")
    )
    transaction_obj = None

    if reference:
        transaction_obj = Transaction.objects.filter(
            transaction_identifier=reference
        ).first()

    context = {
        "message": "Payment completed successfully.",
        "reference": reference,
        "transaction": transaction_obj,
    }

    return render(request, "payments/success.html", context)
