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
    # ฟิลด์ย่อยสำหรับ statement
    field1 = forms.CharField(
        required=True,
        label="Field 1",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter name'})
    )
    field2 = forms.IntegerField(
        required=True,
        label="Field 2",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Amount'})
    )
    field3 = forms.ChoiceField(
        required=True,
        label="Field 3",
        choices=[("choice1", "Income"), ("choice2", "Outcome")],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Preset
        fields = ['name']

    def __init__(self, *args, **kwargs):
        # รับ instance จาก Preset (object ที่แก้ไข)
        instance = kwargs.get('instance')
        if instance and instance.statement:
            initial = kwargs.setdefault('initial', {})
            # ดึงค่าจาก statement เพื่อใส่ในฟิลด์ย่อย
            initial['field1'] = instance.statement.get('field1', '')
            initial['field2'] = instance.statement.get('field2', '')
            initial['field3'] = instance.statement.get('field3', '')
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # รวมค่าจากฟิลด์ย่อยเป็น statement
        instance.statement = {
            "field1": self.cleaned_data.get('field1'),
            "field2": self.cleaned_data.get('field2'),
            "field3": self.cleaned_data.get('field3')
        }
        if commit:
            instance.save()
        return instance
