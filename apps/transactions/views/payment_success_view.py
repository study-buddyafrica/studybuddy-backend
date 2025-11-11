from django.shortcuts import render

def deposit_success_view(request):
    """
    Page users are redirected to after successful payment
    """
    tracking_id = request.GET.get('tracking_id')
    checkout_id = request.GET.get('checkout_id')
    
    context = {
        'tracking_id': tracking_id,
        'checkout_id': checkout_id,
        'message': 'Payment completed successfully! Your wallet will be updated shortly.'
    }
    
    return render(request, 'payments/success.html', context)
