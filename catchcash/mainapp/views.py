from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse

from .models import Account, FixStatement, Mission, Preset, Scope, Wallet, Statement
from .forms import WalletFilterForm, StatementForm

# Create your views here.

def setting(request):
    return render(request, 'setting.html')

def main(request):
    account = request.user.account  # Account ของผู้ใช้ปัจจุบัน
    theme = account.appTheme

    form = WalletFilterForm(request.GET or None, account=account)
    statements = Statement.objects.none()  # เริ่มต้นด้วยการไม่มีข้อมูล
    wallet = Wallet.objects.none()
    sData = {}
    status = "ไม่พบการจำกัดวงเงิน"
    sList_gByD = []

    if request.method == 'GET':
        if form.is_valid():
            wallet = form.cleaned_data.get('wallet') or account.wallets.first()
            date = form.cleaned_data.get('date')
            statements = Statement.objects.filter(wallet=wallet)

            if date:
                statements = statements.filter(addDate=date)
            statements = statements.order_by('type')
        else:
            wallet = account.wallets.first()
            statements = Statement.objects.filter(wallet=wallet).order_by('type')

        income, out = 0, 0
        for s in statements:
            if s.type == "in":
                income += s.amount
            else:
                out += s.amount

        sData = {"in": income, "out": out}

        unique_add_dates_list = list(set(statements.values_list('addDate', flat=True)))
        sList_gByD = []
        for d in unique_add_dates_list:
            sList_D = statements.filter(addDate=d)
            in_D, out_D = 0, 0
            for s in sList_D:
                if s.type == "in":
                    in_D += s.amount
                else:
                    out_D += s.amount
            sList_gByD.append({
                "statements": sList_D,
                "in": f"{in_D:.2f}",
                "out": f"{out_D:.2f}"
            })

        choices = [("other", "Other")]
        categories = wallet.get_categories() if wallet else []
        choices += [(category, category) for category in categories]

        if wallet and wallet.scopes.exists():
            status = "scopes-exists"

    return render(request, 'main.html', {
        'form': form,
        'statements': sList_gByD,
        'choices': choices,
        'wallet': wallet,
        'theme': theme,
        "data": sData,
        "status": status
    })


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
            if(request.POST.get('addDate')!=""):
                statement.addDate = request.POST.get('addDate')
            statement.wallet = wallet  # กำหนด wallet ให้กับ statement
            statement.category = category  # กำหนด category ให้กับ statement
            statement.save()  # บันทึก statement ลงฐานข้อมูล

            return redirect(request.META.get('HTTP_REFERER', '/'))  # กลับไปที่หน้า main
    else:
        wallet_id = request.GET.get('wallet_id')
        wallet = Wallet.objects.get(id=wallet_id)
        choices = [(category, category) for category in wallet.get_categories()]
        choices.append(("other", "Other"))  # เพิ่มตัวเลือก "other"

        form = StatementForm(wallet=wallet)

    return HttpResponse("ERROR, Can't add_statement")

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
            if(request.POST.get('addDate')!=""):
                statement.addDate = request.POST.get('addDate')
            statement.category = category  # กำหนด category ให้กับ statement
            statement.save()  # บันทึก statement ลงฐานข้อมูล
            return redirect(request.META.get('HTTP_REFERER', '/'))  # กลับไปที่หน้า main
    else:
        form = StatementForm(instance=Statement.objects.get(id=id))
    return HttpResponse("ERROR, Can't edit_statement")
    
def delete_statement(request, id):
    statement = Statement.objects.get(id=id)
    statement.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))  # กลับไปที่หน้า main



def create_wallet(request):
    if request.method == 'POST':
        # รับข้อมูลจากฟอร์ม
        wName = request.POST.get('wName')
        currency = request.POST.get('currency')
        listCategory = request.POST.getlist('listCategory[]')  # รับหมวดหมู่ในรูปแบบ JSON

        # สร้าง Wallet ใหม่
        account = request.user.account
        wallet = Wallet(account=account, wName=wName, currency=currency, listCategory=listCategory)
        wallet.save()

        return redirect(request.META.get('HTTP_REFERER', '/'))  # กลับไปที่หน้า main หลังบันทึก
    return HttpResponse("ERROR, Can't create_wallet")



def create_fixstatement(request):
    if request.method == 'POST':
        wallet_id = request.POST['wallet']
        amount = request.POST['amount']
        type = request.POST['type']
        category = request.POST['category']
        frequency = request.POST['frequency']

        wallet = Wallet.objects.get(id=wallet_id)

        new_fixstatement = FixStatement(
            wallet=wallet,
            amount=amount,
            type=type,
            category=category,
            frequency=frequency
        )
        new_fixstatement.save()
        messages.success(request, 'FixStatement ถูกสร้างสำเร็จแล้ว')
        return redirect(reverse('wallet_detail', args=[wallet_id]))

    wallets = Wallet.objects.all()
    return HttpResponse("ERROR, Can't create_fixstatement")

def create_scope(request):
    if request.method == 'POST':
        wallet_id = request.POST['wallet']
        amount = request.POST['amount']
        type = request.POST['type']
        category = request.POST['category']
        range = request.POST['range']

        wallet = Wallet.objects.get(id=wallet_id)

        new_scope = Scope(
            wallet=wallet,
            amount=amount,
            type=type,
            category=category,
            range=range
        )
        new_scope.save()
        messages.success(request, 'Scope ถูกสร้างสำเร็จแล้ว')
        return redirect(reverse('wallet_detail', args=[wallet_id]))

    wallets = Wallet.objects.all()
    return HttpResponse("ERROR, Can't create_scope")

def create_mission(request):
    if request.method == 'POST':
        wallet_id = request.POST['wallet']
        mName = request.POST['mName']
        amount = request.POST['amount']
        dueDate = request.POST['dueDate']
        pic = request.FILES.get('pic', None)

        wallet = Wallet.objects.get(id=wallet_id)

        new_mission = Mission(
            wallet=wallet,
            mName=mName,
            amount=amount,
            dueDate=dueDate,
            pic=pic
        )
        new_mission.save()
        messages.success(request, 'Mission ถูกสร้างสำเร็จแล้ว')
        return redirect(reverse('wallet_detail', args=[wallet_id]))

    wallets = Wallet.objects.all()
    return HttpResponse("ERROR, Can't create_mission")

def create_preset(request):
    if request.method == 'POST':
        wallet_id = request.POST['wallet']
        name = request.POST['name']

        wallet = Wallet.objects.get(id=wallet_id)

        new_preset = Preset(
            wallet=wallet,
            name=name
        )
        new_preset.save()
        messages.success(request, 'Preset ถูกสร้างสำเร็จแล้ว')
        return redirect(reverse('wallet_detail', args=[wallet_id]))

    wallets = Wallet.objects.all()
    return HttpResponse("ERROR, Can't create_preset")

def scope(request):
    account = request.user.account
    if request.method == 'GET':
        
        form = WalletFilterForm(request.GET or None, account=account)
        choices = [("other", "Other")]
        
        if account.wallets.exists():
            if form.is_valid():
                wallet = form.cleaned_data.get('wallet') if form.is_valid() else account.wallets.first()
                date = form.cleaned_data.get('date')

                statements = Statement.objects.filter(wallet=wallet)

                if date:
                    statements = statements.filter(addDate=date)
                    
            else:
                wallet = account.wallets.first()
                statements = Statement.objects.filter(wallet=wallet)

            income = 0
            out = 0
            for s in statements:
                if s.type == "in":
                    income += s.amount
                else:
                    out += s.amount
                    
            sData = {"in":income, "out":out}
                
            categories = wallet.get_categories()  # ดึง categories จาก wallet
            choices += [(category, category) for category in categories]

    return render(request, 'scope.html', {
        'sData' : sData,
        'statements': statements
        }) #ขอใส่เพื่อให้รัน  test ได้

def wallet_detail(request, id):
    return HttpResponse("This view is not yet implemented.")

def progression(request):
    return render(request, 'progression.html')

def trophy(request):
    return render(request, 'trophy.html')

def about(request):
    return render(request, 'about.html')
