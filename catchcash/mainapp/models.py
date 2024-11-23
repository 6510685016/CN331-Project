from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.db.models import Sum
from django.utils.timezone import now

# ACCOUNTS model
class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    appTheme = models.CharField(max_length=100)
    joinDate = models.DateField(auto_now_add=True)
    reward = models.IntegerField(default=0)
    lastLoginDate = models.DateField(auto_now_add=True)
    trophy = models.CharField(max_length=100, null=True, blank=True)
    profile_pic = models.ImageField(upload_to='profile_photos/',  default='profile_photos/default.jpg')
    
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
        
    def add_category(self, category):
        if category not in self.listCategory and category not in [None, "None", "other", "Other"]:
            self.listCategory.append(category)
            self.save()

    def remove_category(self, category):
        if category in self.listCategory:
            self.listCategory.remove(category)
            self.save()

    def get_categories(self):
        return self.listCategory
    
    def balance(self):
        # Calculate the balance based on related statements
        # Sum of 'in' type statements (add) and subtract 'out' type statements (spend)
        total_in = self.statements.filter(type='in').aggregate(Sum('amount'))['amount__sum'] or 0
        total_out = self.statements.filter(type='out').aggregate(Sum('amount'))['amount__sum'] or 0
        return f"{total_in - total_out:.2f}"

class Scope(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='scopes', on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=3, choices=[('in', 'In'), ('out', 'Out')])
    range = models.CharField(max_length=2, choices=[('1D', '1 Day'), ('1W', '1 Week'), ('1M', '1 Month'), ('1Y', '1 Year')])

    def __str__(self):
        return f"Scope: {self.category} ({self.range})"
    
    def status(self, date):
        statements = Statement.objects.filter(wallet=self.wallet)
        
        # กรอง Statements ตามช่วงเวลา
        if self.range == "1D":  # วันเดียว
            statements = statements.filter(addDate=date)
        elif self.range == "1W":  # สัปดาห์
            start_week = date - timedelta(days=date.weekday())  # วันจันทร์ของสัปดาห์
            end_week = start_week + timedelta(days=6)  # วันอาทิตย์
            statements = statements.filter(addDate__range=[start_week, end_week])
        elif self.range == "1M":  # เดือน
            statements = statements.filter(addDate__year=date.year, addDate__month=date.month)
        elif self.range == "1Y":  # ปี
            statements = statements.filter(addDate__year=date.year)
        
        # คำนวณผลรวมของ Statements
        total_in = statements.filter(type="เก็บเงิน").aggregate(Sum('amount'))['amount__sum'] or 0
        total_out = statements.filter(type="ควบคุมการใช้เงิน").aggregate(Sum('amount'))['amount__sum'] or 0
        
        current_total = total_in - total_out
        
        if self.type == "in":  # เป้าหมายเงินเข้า
            return self.amount - total_in
        elif self.type == "out":  # เป้าหมายเงินออก
            return  total_out - self.amount 

    def statusToText(self):
        date = now().date()
        status = self.status(date)
        if status > 0: #ไม่ตรงเป้า
            if self.type == "in": 
                return f"Income less then target by {status}."
            else:
                return f"Spent {status} more than planned."
        else:  # status < 0
            return "On target."
        

class Preset(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='presets', on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)
    statement = models.JSONField(default=list)

    def __str__(self):
        return self.name


class Statement(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='statements', on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=3, choices=[('in', 'In'), ('out', 'Out')])
    category = models.CharField(max_length=100)
    addDate = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.wallet} - {self.amount} ({self.type})"

class Mission(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='missions', on_delete=models.CASCADE, null=True)
    mName = models.CharField(max_length=100)
    dueDate = models.DateField()
    curAmount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    pic = models.ImageField(upload_to='missions/', null=True, blank=True)

    def __str__(self):
        return self.mName
    
    def amountToGo(self):
        return max(self.amount - self.curAmount, 0)
    
    def donate(self, money):
        # ตรวจสอบเงินบริจาค
        if money <= 0:
            raise ValidationError("Amount must be greater than 0.")
        if money > self.amountToGo():
            raise ValidationError("Amount exceeds the target left.")
        
        # สร้าง Statement รายการใหม่
        Statement.objects.create(
            wallet=self.wallet,
            amount=money,
            type='out',
            category=f"แบ่งจ่ายรายการใหญ่",
            addDate=timezone.now()
        )
        
        # อัปเดต curAmount
        money = Decimal(money)
        self.curAmount = self.curAmount + money
        self.save()
        return self.curAmount
    
    def isOutdate(self):
        return timezone.now().date() > self.dueDate
    
    def status_text(self):
        if self.isOutdate() or self.amountToGo() == 0:
            return f"[{self.mName}] {self.curAmount}/{self.amount}{self.wallet.currency} ({self.curAmount/self.amount*100:.2f}%)"
        else:
            return f"[{self.mName}] {self.amountToGo()}{self.wallet.currency} more!"