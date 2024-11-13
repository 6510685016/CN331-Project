from django.shortcuts import get_object_or_404, render, redirect

from .models import Account, Wallet, Statement
from .forms import WalletFilterForm, StatementForm

# Create your views here.

def login(request):
    return render(request, 'login.html')

def main(request):
    account = request.user.account # Account ของผู้ใช้ปัจจุบัน
    theme = account.appTheme
    
    form = WalletFilterForm()
    statements = Statement.objects.none()  # เริ่มต้นด้วยการไม่มีข้อมูล
    wallet = Wallet.objects.none()
    
    if request.method == 'GET':
        form = WalletFilterForm(request.GET or None, account=account)
        choices = [("other", "Other")]
        
        if account.wallets.exists():
            if form.is_valid():
                wallet = form.cleaned_data.get('wallet') if form.is_valid() else account.wallets.first()
                start_date = form.cleaned_data.get('start_date')
                end_date = form.cleaned_data.get('end_date')

                statements = Statement.objects.filter(wallet=wallet)

                if start_date:
                    statements = statements.filter(addDate__gte=start_date)
                if end_date:
                    statements = statements.filter(addDate__lte=end_date)
                    
            else:
                wallet = account.wallets.first()
                statements = Statement.objects.filter(wallet=wallet)
                
            categories = wallet.get_categories()  # ดึง categories จาก wallet
            choices += [(category, category) for category in categories]

        else:
            statements = Statement.objects.none()  # ถ้าไม่มี wallet

    return render(request, 'main.html', {'form': form, 'statements': statements, 'choices': choices, 'wallet': wallet, 'theme':theme})

def about(request):
    return render(request, 'about.html')

def analysis(request):
    data = [10, 20, 30, 40, 50]
    labels = ["A", "B", "C", "D", "E"]

    return render(request, 'analysis.html', {'data': data, 'labels': labels})





def add_statement(request):
    if request.method == 'POST':
        wallet_id = request.POST.get('wallet_id')  # รับ wallet_id จาก POST
        wallet = Wallet.objects.get(id=wallet_id)  # ดึง wallet จาก id ที่ได้รับ
        form = StatementForm(request.POST)

        if form.is_valid():
            category = form.cleaned_data.get('category')

            if category == 'other':  # ถ้าผู้ใช้เลือก "other"
                custom_category = request.POST.get('custom_category')
                if custom_category:  # ถ้ามีการกรอกหมวดหมู่เอง
                    category = custom_category  # ใช้ค่าที่กรอก

            # ตรวจสอบหมวดหมู่ที่ได้รับ
            if category:
                # ถ้าหมวดหมู่ไม่ใช่ "None" ก็เพิ่มหมวดหมู่ใหม่
                wallet.add_category(category)

            statement = form.save(commit=False)  # สร้าง instance ของ statement โดยไม่บันทึก
            statement.wallet = wallet  # กำหนด wallet ให้กับ statement
            statement.category = category  # กำหนด category ให้กับ statement
            statement.save()  # บันทึก statement ลงฐานข้อมูล

            return redirect('main')  # กลับไปที่หน้า main
    else:
        wallet_id = request.GET.get('wallet_id')
        wallet = Wallet.objects.get(id=wallet_id)
        choices = [(category, category) for category in wallet.get_categories()]
        choices.append(("other", "Other"))  # เพิ่มตัวเลือก "other"

        form = StatementForm(choices=choices)

    return render(request, 'add_statement.html', {
        'form': form,
        'choices': choices,
        'wallet': wallet
    })

def edit_statement(request, id):
    if request.method == 'POST':
        statement = Statement.objects.get(id=id)
        form = StatementForm(request.POST, instance=statement)
        
        if form.is_valid():
            category = request.POST.get('category')
            if category == 'other':  # ถ้าผู้ใช้เลือก "other"
                custom_category = request.POST.get('custom_category')
                if custom_category:  # ถ้ามีการกรอกหมวดหมู่เอง
                    category = custom_category  # ใช้ค่าที่กรอก

            # ตรวจสอบหมวดหมู่ที่ได้รับ
            if category:
                statement.wallet.add_category(category)
            
            statement = form.save(commit=False)
            statement.category = category  # กำหนด category ให้กับ statement
            statement.save()  # บันทึก statement ลงฐานข้อมูล
            return redirect('main')  # กลับไปที่หน้า main
    else:
        form = StatementForm(instance=Statement.objects.get(id=id))
    return render(request, 'edit_statement.html', {'form': form})
    
def delete_statement(request, id):
    statement = Statement.objects.get(id=id)
    statement.delete()
    return redirect('main')  # กลับไปที่หน้า main
