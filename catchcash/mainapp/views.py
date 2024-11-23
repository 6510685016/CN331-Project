from django.utils import timezone
from django.contrib import messages
from django.forms import ValidationError
from django.http import HttpResponse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.timezone import now

from .models import Account, Mission, Preset, Scope, Wallet, Statement
from .forms import MissionForm, PresetForm, ScopeForm, WalletFilterForm, StatementForm

# Create your views here.

def setting(request):
    return render(request, 'setting.html')

def main(request):
    account = request.user.account  # Account ของผู้ใช้ปัจจุบัน
    theme = account.appTheme

    if not account.wallets.exists():
        # ถ้าไม่มี Wallet ให้สร้าง Wallet เริ่มต้น
        default_wallet = Wallet.objects.create(account=account, wName="Default Wallet")
        return redirect('main')
    
    wallet = None
    presets = Preset.objects.filter(wallet__in=account.wallets.all())
    form = WalletFilterForm(request.GET or None, account=account)
    statements = Statement.objects.none()  # เริ่มต้นด้วยการไม่มีข้อมูล
    wallet = Wallet.objects.none()
    sData = {}
    missions = Mission.objects.none()
    scopes = Scope.objects.none()
    status = "ไม่พบการจำกัดวงเงิน"
    sList_gByD = []
    date = now().date()

    if form.is_valid():
        wallet = form.cleaned_data.get('wallet') or wallet  # ดึง wallet ที่ผู้ใช้เลือก
    if not wallet:
        wallet = account.wallets.first()
    if wallet:
        presets = Preset.objects.filter(wallet=wallet)
    else:
        presets = Preset.objects.none()

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
        sorted_unique_add_dates_list = sorted(unique_add_dates_list, reverse=True)
        sList_gByD = []
        for d in sorted_unique_add_dates_list:
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

        choices = [ ("รายรับ", "รายรับ"),
                    ("อาหารและเครื่องดื่ม", "อาหารและเครื่องดื่ม"), 
                    ("ค่าเดินทาง", "ค่าเดินทาง"), 
                    ("จิปาถะ", "จิปาถะ"), 
                    ("บันเทิง", "บันเทิง"), 
                    ("ครอบครัว", "ครอบครัว"), 
                    ("ของใช้ส่วนตัว", "ของใช้ส่วนตัว"), 
                    ("ค่าใช้จ่ายประจำ", "ค่าใช้จ่ายประจำ"), 
                    ("ช็อปปิ้ง", "ช็อปปิ้ง"), 
                    ]
        categories = wallet.get_categories() if wallet else []
        choices += [(category, category) for category in categories]

        if wallet and wallet.scopes.exists():
            scopes = Scope.objects.filter(wallet=wallet)

        if wallet and wallet.missions.exists():
            missions = Mission.objects.filter(wallet=wallet)
            
    return render(request, 'main.html', {
        'form': form,
        'statements': sList_gByD,
        'choices': choices,
        'wallet': wallet,
        'theme': theme,
        "data": sData,
        "scopes": scopes,
        "missions": missions,
        "status": status,
        'presets': presets,
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

def create_scope(request):
    if request.method == 'POST':
        # รับค่าจากฟอร์ม
        wallet_id = request.POST.get('wallet')  # ดึงค่า wallet ที่ถูกส่งมาจากฟอร์ม
        amount = request.POST.get('amount')
        type = request.POST.get('type')
        range_value = request.POST.get('range')

        try:
            # ดึง wallet ที่เลือก
            wallet = Wallet.objects.get(id=wallet_id)

            # สร้าง Scope ใหม่
            new_scope = Scope(
                wallet=wallet,
                amount=amount,
                type=type,
                range=range_value
            )
            new_scope.save()

            messages.success(request, 'Scope ถูกสร้างสำเร็จแล้ว')
            return redirect('main')  # เปลี่ยนเป็น URL ที่ต้องการ

        except Wallet.DoesNotExist:
            messages.error(request, 'ไม่พบกระเป๋าเงินที่เลือก')
            return redirect('main')  # หรือ URL ที่ต้องการให้กลับไป
    else:
        # ถ้าเป็น GET ก็แสดงแบบฟอร์ม
        return HttpResponse("ERROR, Can't create_scope")


def delete_scope(request, scope_id):
    scope = get_object_or_404(Scope, id=scope_id)
    wallet_id = scope.wallet.id  # เก็บ wallet_id ก่อนลบ scope
    scope.delete()
    return redirect('scope', wallet_id=wallet_id)

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
        messages.success(request, 'Goal ถูกสร้างสำเร็จแล้ว')
        return redirect('goal', wallet_id=mission.wallet.id)

    wallets = Wallet.objects.all()
    return HttpResponse("ERROR, Can't create_mission")

def edit_mission(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)

    if request.method == 'POST':
        form = MissionForm(request.POST, request.FILES, instance=mission)
        if form.is_valid():
            form.save()
            return redirect('goal', wallet_id=mission.wallet.id)
    else:
        form = MissionForm(instance=mission)

    return render(request, 'edit_mission.html', {'form': form, 'mission': mission})

def delete_mission(request, mission_id):
    mission = get_object_or_404(Mission, id=mission_id)
    wallet_id = mission.wallet.id  # เก็บ wallet_id ก่อนลบ mission
    mission.delete()
    return redirect('goal', wallet_id=wallet_id)


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
        messages.success(request, 'Scope ถูกสร้างสำเร็จแล้ว')
        return redirect('main')

    wallets = Wallet.objects.all()
    return HttpResponse("ERROR, Can't create_preset")

def scope(request, wallet_id):
    wallet = get_object_or_404(Wallet, id=wallet_id)
    scopes = Scope.objects.filter(wallet=wallet)

    if request.method == 'POST':
        form = ScopeForm(request.POST)
        if form.is_valid():
            scope = form.save(commit=False)
            scope.wallet = wallet
            scope.save()
            return redirect('scope', wallet_id=wallet.id)
    else:
        form = ScopeForm()

    return render(request, 'scope.html', {
        'wallet': wallet,
        'scopes': scopes,
        'form': form,
    })

def edit_scope(request, scope_id):
    scope = get_object_or_404(Scope, id=scope_id)

    if request.method == 'POST':
        form = ScopeForm(request.POST, instance=scope)
        if form.is_valid():
            form.save()
            return redirect('scope', wallet_id=scope.wallet.id)
    else:
        form = ScopeForm(instance=scope)

    return render(request, 'edit_scope.html', {'form': form, 'scope': scope})

def edit_scope(request, scope_id):
    scope = get_object_or_404(Scope, id=scope_id)

    if request.method == 'POST':
        form = ScopeForm(request.POST, instance=scope)
        if form.is_valid():
            form.save()
            return redirect('scope', wallet_id=scope.wallet.id)
    else:
        form = ScopeForm(instance=scope)

    return render(request, 'edit_scope.html', {'form': form, 'scope': scope})

def wallet_detail(request, id):
    return HttpResponse("This view is not yet implemented.")

def progression(request):
    return render(request, 'progression.html')

def trophy(request):
    return render(request, 'trophy.html')

def about(request):
    return render(request, 'about.html')

def mission(request, wallet_id):
    wallet = get_object_or_404(Wallet, id=wallet_id)
    missions = Mission.objects.filter(wallet=wallet)

    if request.method == 'POST':
        form = MissionForm(request.POST, request.FILES)
        if form.is_valid():
            mission = form.save(commit=False)
            mission.wallet = wallet
            mission.save()
            return redirect('goal', wallet_id=wallet.id)
    else:
        form = MissionForm()

    return render(request, 'mission.html', {
        'wallet': wallet,
        'missions': missions,
        'form': form,
    })


def donate_to_mission(request, mission_id):
    if request.method == "POST":
        mission = get_object_or_404(Mission, id=mission_id)
        try:
            donate_amount = float(request.POST.get('donate_amount', 0))
            mission.donate(donate_amount)  
            messages.success(request, f"Donated {donate_amount} successfully!")
        except ValidationError as e:
            messages.error(request, e.message)
        except ValueError:
            messages.error(request, "Invalid donation amount.")
        return redirect(request.META.get('HTTP_REFERER', '/'))
    return HttpResponse("ERROR, Can't donate_to_mission")

def preset(request, wallet_id):
    account = request.user.account  # Account ของผู้ใช้ปัจจุบัน
    theme = account.appTheme

    # ดึงข้อมูล Wallet และ Preset ที่เกี่ยวข้อง
    wallet = get_object_or_404(Wallet, id=wallet_id, account=account)
    presets = Preset.objects.filter(wallet=wallet)

    # สร้างฟอร์มใหม่สำหรับการเพิ่ม Preset
    if request.method == 'POST':
        form = PresetForm(request.POST)
        if form.is_valid():
            new_preset = form.save(commit=False)
            new_preset.wallet = wallet
            new_preset.save()
            # Redirect กลับไปหน้าเดิมหลังการบันทึก
            return redirect('preset', wallet_id=wallet.id)
    else:
        form = PresetForm()

    return render(request, 'preset.html', {
        'form': form,
        'wallet': wallet,
        'presets': presets,
        'theme': theme,
        })

from django.shortcuts import get_object_or_404, redirect

def edit_preset(request, preset_id):
    preset = get_object_or_404(Preset, id=preset_id)
    if request.method == 'POST':
        form = PresetForm(request.POST, instance=preset)
        if form.is_valid():
            form.save()
            if preset.wallet and preset.wallet.id:
                return redirect('preset', wallet_id=preset.wallet.id)
    else:
        form = PresetForm(instance=preset)
    return render(request, 'edit_preset.html', {'form': form})

def delete_preset(request, preset_id):
    preset = get_object_or_404(Preset, id=preset_id)
    wallet_id = preset.wallet.id
    preset.delete()
    return redirect('preset', wallet_id=wallet_id)


def use_preset(request, preset_id):
    if request.method == 'POST':  # ใช้ POST เพื่อรับค่า
        preset = get_object_or_404(Preset, id=preset_id)
        
        # ดึงข้อมูลจาก JSONField `statement`
        statement_data = preset.statement
        
        # ตรวจสอบข้อมูลใน JSONField และสร้าง Statement ใหม่
        category = statement_data.get('field1', 'อื่นๆ')  # Default 'อื่นๆ' หากไม่มีข้อมูล
        amount = statement_data.get('field2', 0.0)
        type_text = statement_data.get('field3', 'out')  # Default 'out' หากไม่มีข้อมูล

         # แปลงค่า `field3` เป็น `type` ของ Statement
        if type_text == 'รายรับ':
            type_ = 'in'  # ใช้ 'in' สำหรับรายรับ
        elif type_text == 'รายจ่าย':
            type_ = 'out'  # ใช้ 'out' สำหรับรายจ่าย
        
        # สร้าง Statement ใหม่
        statement = Statement.objects.create(
            wallet=preset.wallet,  # ใช้ Wallet เดียวกับที่ Preset อ้างอิง
            category=category,
            amount=amount,
            type=type_
        )
        statement.save()
        
        # ส่ง JSON Response กลับมา (กรณีใช้ AJAX)
        return JsonResponse({'success': True, 'message': 'Statement created successfully.'})
    
    # หากไม่ใช่ POST ให้ส่งสถานะไม่อนุญาต
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
