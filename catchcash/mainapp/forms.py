# forms.py
from django import forms
from .models import Wallet, Statement
from .models import Preset

class WalletFilterForm(forms.Form):
    wallet = forms.ModelChoiceField(
        queryset=Wallet.objects.none(),
        label="Select Wallet",
        empty_label=None,
        widget=forms.Select(attrs={'class': 'WalletFilterForm'})
    )
    date = forms.DateField(
        widget=forms.TextInput(attrs={'type': 'date', 'class': ' WalletFilterForm'}),
        required=False,
        label="เลือกวันที่"
    )
    
    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account', None)
        super(WalletFilterForm, self).__init__(*args, **kwargs)

        if account:
            # กำหนด queryset ของฟิลด์ wallet ให้แสดงเฉพาะ wallet ของ account นั้น
            if account.wallets.exists():
                self.fields['wallet'].queryset = Wallet.objects.filter(account=account)
            else:
                self.fields['wallet'].empty_label = "ไม่พบ Wallet"
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
    
class PresetForm(forms.ModelForm):
    class Meta:
        model = Preset
        fields = ['name', 'statement']  # ใช้เฉพาะฟิลด์ที่ต้องการ
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Preset Name'
            }),
            'statement': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Statement as JSON',
                'rows': 3
            }),
        }