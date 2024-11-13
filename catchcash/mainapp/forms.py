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
    category = forms.CharField(label='Category', required=False)

    class Meta:
        model = Statement
        fields = ['amount', 'type', 'category']

    def __init__(self, *args, **kwargs):
        wallet = kwargs.pop('wallet', None)  # รับ wallet ที่ส่งมาจาก views.py
        super(StatementForm, self).__init__(*args, **kwargs)

        if wallet:
            # ดึง category จาก wallet และสร้างเป็นตัวเลือกให้กับผู้ใช้
            categories = wallet.get_categories()
            choices = [(category, category) for category in categories]

            # กำหนดค่าเริ่มต้นสำหรับ category จาก instance (ค่าเดิม)
            selected_category = self.instance.category if self.instance else None

            self.fields['category'] = forms.ChoiceField(
                choices=choices + [("other", "Other")],  # เพิ่มตัวเลือกสำหรับกรอกเอง
                label='Category',
                required=False,
                initial=selected_category  # กำหนด category เดิมให้เป็นค่าเริ่มต้น
            )

    def clean_category(self):
        category = self.cleaned_data.get('category')
        custom_category = self.cleaned_data.get('custom_category')  # ค่าจากฟิลด์ custom_category ที่กรอกเอง

        if category == 'other' and custom_category:
            return custom_category  # ถ้าเลือก "other" และกรอกหมวดหมู่เอง ให้ใช้ค่าจาก custom_category

        return category  # ถ้าไม่เลือก "other" ก็ใช้ค่า category ที่เลือก