from django.shortcuts import get_object_or_404, render, redirect

from .models import Account, Wallet, Statement
from .forms import WalletFilterForm, StatementForm

# Create your views here.

def login(request):
    return render(request, 'login.html')

def main(request):
    form = WalletFilterForm()

    statements = Statement.objects.none()  # เริ่มต้นด้วยการไม่มีข้อมูล
    wallet = Wallet.objects.none()
    
    if request.method == 'GET':
        account = request.user.account  # อ้างอิง Account ของผู้ใช้ปัจจุบัน
        form = WalletFilterForm(request.GET or None, account=account)
        
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
    
        else:
            statements = Statement.objects.none()  # ถ้าไม่มี wallet

    return render(request, 'main.html', {'form': form, 'statements': statements, 'wallet': wallet})

def about(request):
    return render(request, 'about.html')

def analysis(request):
    data = [10, 20, 30, 40, 50]
    labels = ["A", "B", "C", "D", "E"]

    return render(request, 'analysis.html', {'data': data, 'labels': labels})





def add_statement(request):
    if request.method == 'POST':
        form = StatementForm(request.POST)
        if form.is_valid():
            wallet_id = request.POST.get('wallet_id') # รับ wallet
            wallet = Wallet.objects.get(id=wallet_id)
            
            statement = form.save(commit=False)  # สร้าง instance ของ statement โดยไม่บันทึกลงฐานข้อมูลทันที
            statement.wallet = wallet   # กำหนด wallet ให้กับ statement
            statement.save()  # บันทึก statement ลงฐานข้อมูล
            return redirect('main')  # กลับไปที่หน้า main
    else:
        form = StatementForm()

    return render(request, 'add_statement.html', {'form': form})

def edit_statement(request, id):
    print("hello")
    if request.method == 'POST':
        statement = Statement.objects.get(id=id)
        form = StatementForm(request.POST, instance=statement)
        
        if form.is_valid():
            form.save()  # บันทึกการเปลี่ยนแปลง
            return redirect('main')  # กลับไปที่หน้า main
    else:
        form = StatementForm(instance=Statement.objects.get(id=id))
    
    return render(request, 'edit_statement.html', {'form': form})
    
def delete_statement(request, id):
    statement = Statement.objects.get(id=id)
    statement.delete()
    return redirect('main')  # กลับไปที่หน้า main