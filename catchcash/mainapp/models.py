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
    wallet = models.ForeignKey('Wallet', related_name='scopes', on_delete=models.CASCADE)
    month = models.PositiveIntegerField()  # เดือน (1-12)
    year = models.PositiveIntegerField()  # ปี
    income_goal = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # เป้าหมายรายรับ
    expense_goal = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # เป้าหมายรายจ่าย

    class Meta:
        unique_together = ('wallet', 'month', 'year')

    def __str__(self):
        return f"{self.wallet} - {self.month}/{self.year}"

    def calculate_status(self, date=None):
        
        if not date:
            date = now().date()

        # ตรวจสอบว่าเดือนและปีใน date == MonthlyGoal 
        if date.month != self.month or date.year != self.year:
            return {
                "income_message": "ไม่พบข้อมูลเป้าหมายสำหรับเดือนนี้",
                "expense_message": "ไม่พบข้อมูลเป้าหมายสำหรับเดือนนี้",
                "income_diff": None,
                "expense_diff": None,
            }

        # กรอง Statements ตามเดือนและปี
        statements = self.wallet.statements.filter(
            addDate__year=self.year,
            addDate__month=self.month
        )

        # คำนวณยอดรายรับและรายจ่ายรวม
        total_income = statements.filter(type="in").aggregate(models.Sum('amount'))['amount__sum'] or 0
        total_expense = statements.filter(type="out").aggregate(models.Sum('amount'))['amount__sum'] or 0

        # แสดงสถานะ -> str
        income_diff = total_income - self.income_goal
        expense_diff = total_expense - self.expense_goal

        return {
            "income_diff": income_diff,
            "expense_diff": expense_diff,
            "income_message": (
                f"รายรับเดือนนี้ยังน้อยกว่า {self.income_goal} {self.wallet.currency} อยู่ {abs(income_diff):.2f} {self.wallet.currency}" if income_diff < 0 
                else f"รายรับถึงเป้า {self.income_goal} {self.wallet.currency} แล้ว"
            ),
            "expense_message": (
                f"รายจ่ายเดือนนี้เกินกว่า {self.expense_goal} {self.wallet.currency} อยู่ {abs(expense_diff):.2f} {self.wallet.currency}" if expense_diff > 0 
                else f"รายจ่ายยังอยู่ในเป้า {self.expense_goal} {self.wallet.currency}"
            )
        }
        

class Preset(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='presets', on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)
    statement = models.JSONField(default=list)

    def __str__(self):
        return self.name


class Statement(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='statements', on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    type = models.CharField(max_length=3, choices=[('in', 'In'), ('out', 'Out')])
    category = models.CharField(max_length=100)
    addDate = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.wallet} - {self.amount} ({self.type})"

class Mission(models.Model):
    wallet = models.ForeignKey(Wallet, related_name='missions', on_delete=models.CASCADE, null=True)
    mName = models.CharField(max_length=100)
    dueDate = models.DateField()
    curAmount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=20, decimal_places=2)

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