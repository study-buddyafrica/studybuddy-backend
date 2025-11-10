from django.contrib import admin
from apps.transactions.models import Wallet, Transaction

admin.site.register(Wallet)
admin.site.register(Transaction )