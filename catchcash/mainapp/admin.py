from django.contrib import admin
from mainapp.models import Account,Wallet,Scope,Preset,Statement,Mission

# Register your models here.

admin.site.register(Account)
admin.site.register(Wallet)
admin.site.register(Scope)
admin.site.register(Preset)
admin.site.register(Statement)
admin.site.register(Mission)