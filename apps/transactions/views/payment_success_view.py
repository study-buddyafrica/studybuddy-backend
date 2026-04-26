from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from djmoney.money import Money

from apps.transactions.services import process_session_payment
from apps.transactions.models import Wallet

@login_required
def deposit_success_view(request):
    """
    Page users are redirected to after successful payment.
    Intercepts the redirect to trigger the 70/30 wallet split.
    """
    tracking_id = request.GET.get('tracking_id')
    checkout_id = request.GET.get('checkout_id')
    
    # Example: Fetching the actual order details
    # order = Order.objects.get(tracking_id=tracking_id)
    # payment_amount = order.amount
    # teacher = order.teacher
    
    # --- DEMO VALUES ---
    payment_amount = Money(1000.00, 'KES') 
    teacher = None # Replace with actual Teacher User instance
   

    try:
        student_wallet = request.user.wallet
        teacher_wallet = teacher.wallet 

        # Trigger the atomic financial routing
        process_session_payment(
            payment_amount=payment_amount,
            student_wallet=student_wallet,
            teacher_wallet=teacher_wallet
        )

        context = {
            'tracking_id': tracking_id,
            'checkout_id': checkout_id,
            'message': 'Payment completed successfully! The teacher has been credited.'
        }
        
        return render(request, 'payments/success.html', context)

    except ValueError as e:
        # This catches the "Insufficient balance" raised by your withdraw() method
        messages.error(request, f"Payment failed: {str(e)}")
        
        context = {'message': f'Error processing payment: {str(e)}'}
        return render(request, 'payments/success.html', context)
        
    except Exception as e:
        # Catch-all for database drops or missing wallets
        messages.error(request, "A critical system error occurred during routing.")
        
        context = {'message': 'System error. Please contact support with your tracking ID.'}
        return render(request, 'payments/success.html', context)