# forms.py
from django import forms
from .models import Wallet, Statement

class WalletFilterForm(forms.Form):
    wallet = forms.ModelChoiceField(
        queryset=Wallet.objects.none(),  # เริ่มต้นด้วย none, จะเซ็ตใหม่ใน __init__
        label="Select Wallet",
        empty_label=None,  # กำหนดให้ไม่มีตัวเลือกว่าง
    )
    start_date = forms.DateField(widget=forms.TextInput(attrs={'type': 'date'}), required=False, label="Start Date")
    end_date = forms.DateField(widget=forms.TextInput(attrs={'type': 'date'}), required=False, label="End Date")

    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account', None)  # รับ account ที่ส่งมาจาก views.py
        super(WalletFilterForm, self).__init__(*args, **kwargs)
        
        if account:
            # กำหนด queryset ของฟิลด์ wallet ให้แสดงเฉพาะ wallet ของ account นั้น
            self.fields['wallet'].queryset = Wallet.objects.filter(account=account)
            
class StatementForm(forms.ModelForm):
    class Meta:
        model = Statement
        fields = ['amount', 'type', 'category']
