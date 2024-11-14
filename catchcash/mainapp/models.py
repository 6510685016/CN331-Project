from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError

# ACCOUNTS model
class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    appTheme = models.CharField(max_length=100)
    joinDate = models.DateField(auto_now_add=True)
    reward = models.IntegerField(default=0)
    lastLoginDate = models.DateField(auto_now_add=True)
    trophy = models.CharField(max_length=100, null=True, blank=True)
    profile_pic = models.ImageField(upload_to='media/profile_photos/', blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    def change_password(self, new_password):
        self.user.set_password(new_password)
        self.user.save()

    def change_theme(self, new_theme):
        self.appTheme = new_theme
        self.save()

    def change_name(self, new_name):
        self.name = new_name
        self.save()

    def change_pic(self, new_pic):
        self.pic = new_pic
        self.save()

# WALLET model
class Wallet(models.Model):
    account = models.ForeignKey(Account, related_name='wallets', on_delete=models.CASCADE)
    wName = models.CharField(max_length=100)
    currency = models.CharField(max_length=10)
    listCategory = models.JSONField(default=list)  # JSONField for categories
    
    def __str__(self):
        return f"Wallet: {self.wName}"

    def add_wallet(self):
        self.save()

    def delete_wallet(self):
        self.delete()
        
    def add_category(self, category):
        if category not in self.listCategory:
            self.listCategory.append(category)
            self.save()

    def remove_category(self, category):
        if category in self.listCategory:
            self.listCategory.remove(category)
            self.save()

    def get_categories(self):
        return self.listCategory


class FixStatement(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='fix_statements', on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=3, choices=[('in', 'In'), ('out', 'Out')])
    category = models.CharField(max_length=100)
    frequency = models.CharField(max_length=2, choices=[('1D', '1 Day'), ('1W', '1 Week'), ('1M', '1 Month'), ('1Y', '1 Year')])

    def add_fix(self):
        self.save()

    def delete_fix(self):
        self.delete()


class Scope(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='scopes', on_delete=models.CASCADE, null=True)
    spendMax = models.DecimalField(max_digits=10, decimal_places=2)
    initTarget = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    range = models.CharField(max_length=2, choices=[('1D', '1 Day'), ('1W', '1 Week'), ('1M', '1 Month'), ('1Y', '1 Year')])

    def __str__(self):
        return f"Scope: {self.category} ({self.range})"
    
    def add_scope(self):
        self.save()

    def delete_scope(self):
        self.delete()


class Preset(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='presets', on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
    def add_preset(self):
        self.save()

    def delete_preset(self):
        self.delete()


class Statement(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='statements', on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=3, choices=[('in', 'In'), ('out', 'Out')])
    category = models.CharField(max_length=100)
    addDate = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet} - {self.amount} ({self.type})"
    
    def add_statement(self):
        self.save()

    def delete_statement(self):
        self.delete()


class Mission(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='missions', on_delete=models.CASCADE, null=True)
    mName = models.CharField(max_length=100)
    dueDate = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    pic = models.ImageField(upload_to='missions/', null=True, blank=True)

    def __str__(self):
        return self.mName
    
    def add_mission(self):
        self.save()

    def delete_mission(self):
        self.delete()