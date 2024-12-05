from django.utils import timezone
from django.db import models
from django.contrib import messages
from django.forms import ValidationError
from django.http import HttpResponse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.contrib.auth import update_session_auth_hash

from .models import Account, Mission, Preset, Scope, Wallet, Statement
from .forms import MissionForm, PresetForm, ScopeForm, WalletFilterForm, StatementForm, SettingForm

# Create your views here.

def welcome(request):
    return render(request,'welcome.html')

def setting(request):
    user = request.user  # รับข้อมูลผู้ใช้ปัจจุบัน
    account = request.user.account  # รับข้อมูลบัญชีผู้ใช้ปัจจุบัน

    # สร้างฟอร์มและผูกข้อมูลกับบัญชีของผู้ใช้
    setting_form = SettingForm(request.POST or None, request.FILES or None, instance=account)

    if request.method == 'POST':  # เมื่อฟอร์มถูกส่ง (POST)
        if setting_form.is_valid():  # ตรวจสอบว่าฟอร์มที่ส่งมาถูกต้องหรือไม่
            for field in setting_form.changed_data:  # ตรวจสอบข้อมูลที่มีการเปลี่ยนแปลงในฟอร์ม
                if field == 'password':  # ถ้าเป็นฟิลด์รหัสผ่าน
                    # ทดสอบการเปลี่ยนรหัสผ่าน
                    user.set_password(setting_form.cleaned_data['password'])  # เปลี่ยนรหัสผ่านของผู้ใช้
                else:
                    setattr(account, field, setting_form.cleaned_data[field])  # อัปเดตข้อมูลอื่น ๆ ที่เปลี่ยนแปลง
            account.save()  # บันทึกการเปลี่ยนแปลงในบัญชีผู้ใช้
            user.save()  # บันทึกการเปลี่ยนแปลงในข้อมูลผู้ใช้

            # ทดสอบการอัปเดต session หลังจากเปลี่ยนรหัสผ่าน
            update_session_auth_hash(request, user)  # อัปเดต session ของผู้ใช้หลังจากเปลี่ยนรหัสผ่าน

            # ทดสอบการเปลี่ยนเส้นทางหลังจากบันทึกข้อมูลสำเร็จ
            return redirect('main')  # เปลี่ยนเส้นทางไปที่หน้าหลัก (main)

    context = {'setting_form': setting_form, 'account': account}  # ส่งข้อมูลฟอร์มและบัญชีผู้ใช้ไปยังเทมเพลต

    return render(request, 'setting.html', context)  # แสดงฟอร์มในหน้า setting.html

def main(request):
    account = request.user.account  # Account ของผู้ใช้ปัจจุบัน
    theme = account.appTheme

    # ตรวจสอบและสร้าง Wallet เริ่มต้นหากไม่มี
    if not account.wallets.exists():
        Wallet.objects.create(account=account, wName="Default Wallet", currency="THB")
        return redirect('main')

    form = WalletFilterForm(request.GET or None, account=account)
    wallet = account.wallets.first()  # ค่าเริ่มต้นเป็น Wallet แรก
    date = now().date()
    dateText = "แสดงทั้งหมด (default)"
    statements = Statement.objects.none()
    presets = Preset.objects.filter(wallet__in=account.wallets.all())
    scopes = Scope.objects.none()
    summary = {"income": 0, "expense": 0, "net": 0}
    status = {}

    if form.is_valid():
        wallet = form.cleaned_data.get('wallet') or wallet  # ดึง wallet ที่ผู้ใช้เลือก
    if wallet:
        presets = Preset.objects.filter(wallet=wallet)
    if request.method == 'GET':
        if form.is_valid():
            wallet = form.cleaned_data.get('wallet') or account.wallets.first()
            date = form.cleaned_data.get('date')
            statements = Statement.objects.filter(wallet=wallet)

            if date:
                statements = statements.filter(addDate=date)
                dateText = "วันที่ " + date.strftime("%d %b %Y")
            else:
                date = now().date()
                dateText = "แสดงทั้งหมด (default)"
            statements = statements.order_by('type')
        else:
            wallet = account.wallets.first()
            statements = Statement.objects.filter(wallet=wallet).order_by('type')

        for s in statements:
            if s.type == "in":
                summary['income'] += s.amount
            else:
                summary['expense'] += s.amount
        summary['net'] = summary['income'] - summary['expense']

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

    # ข้อมูล Goal และ Scope
    if wallet.scopes:
        scopes = wallet.scopes.filter(month=date.month, year=date.year).first()
    if scopes:
        status = scopes.calculate_status(date=date)

    context = {
        "form": form,
        "wallet": wallet,
        'choices': choices,
        "statements": sList_gByD,
        "presets": presets,
        "status": status,
        "summary": summary,
        "theme": theme,
        "date": dateText, #for Header
        "mAndY": f"""{date.strftime("%b, %Y")}""", #for Scope Header
        "Y" : date.year, 
        "M" : date.month, #for Scope Query
        "scopes": scopes,
    }
    return render(request, 'main.html', context)

def goal(request):
    account = request.user.account  # Account ของผู้ใช้ปัจจุบัน
    theme = account.appTheme

    # ตรวจสอบและสร้าง Wallet เริ่มต้นหากไม่มี
    if not account.wallets.exists():
        Wallet.objects.create(account=account, wName="Default Wallet", currency="THB")
        return redirect('main')

    form = WalletFilterForm(request.GET or None, account=account)
    wallet = account.wallets.first()  # ค่าเริ่มต้นเป็น Wallet แรก
    date = now().date()
    goals = Mission.objects.none()

    if form.is_valid():
        wallet = form.cleaned_data.get('wallet') or wallet  # ดึง wallet ที่ผู้ใช้เลือก
    if request.method == 'GET':
        if form.is_valid():
            wallet = form.cleaned_data.get('wallet') or account.wallets.first()
        else:
            wallet = account.wallets.first()
        
    if wallet:
        goals = wallet.missions.all()
            
    context = {
        "form": form,
        "wallet": wallet,
        "goals": goals,
        "theme": theme,
        "date": date,
    }
    return render(request, 'goal.html', context)


def analysis(request):
    # ดึงข้อมูลผู้ใช้ที่เข้าสู่ระบบในปัจจุบัน
    user = request.user
    account = Account.objects.filter(user=user).first()  # ทดสอบ: ตรวจสอบว่าผู้ใช้สามารถดึงข้อมูลบัญชีได้หรือไม่

    # ดึงพารามิเตอร์จากคำขอ GET
    wallet_id = request.GET.get('wallet_id')  # ทดสอบ: ตรวจสอบว่า wallet_id ถูกดึงจาก GET request ถูกต้องหรือไม่
    selected_date = request.GET.get('date')  # ดึงวันที่ที่เลือกจากคำขอ GET  # ทดสอบ: ตรวจสอบว่า selected_date ถูกดึงได้ถูกต้องจากคำขอ GET

    # หากมีการระบุ wallet_id, ให้ดึงข้อมูลกระเป๋าที่ตรงกับ wallet_id และกรองข้อมูล
    if wallet_id:
        try:
            # ดึงข้อมูลกระเป๋าที่เลือก ถ้าพบ
            wallet = account.wallets.get(id=wallet_id)  # ทดสอบ: ตรวจสอบว่าดึงกระเป๋าตาม wallet_id ได้หรือไม่
            # กรองรายการ Statement ตามกระเป๋าที่เลือก
            statements = Statement.objects.filter(wallet=wallet)  # ทดสอบ: ตรวจสอบว่า Statement สามารถกรองตามกระเป๋าได้หรือไม่
            
            # หากมีการระบุวันที่ ให้กรองรายการตามวันที่นั้น
            if selected_date:
                statements = statements.filter(addDate=selected_date)  # ทดสอบ: ตรวจสอบว่า Statement สามารถกรองตามวันที่ได้หรือไม่

            # เตรียมข้อมูล Statement เพื่อส่งกลับไปยัง frontend
            statement_data = []
            for statement in statements:
                statement_data.append({
                    'amount': statement.amount,
                    'type': statement.type,
                    'category': statement.category,
                    'date': statement.addDate
                })

            # ส่งข้อมูลกระเป๋าและรายการ Statement กลับไปยัง frontend ในรูปแบบ JSON
            return JsonResponse({
                'wallet_name': wallet.wName,
                'currency': wallet.currency,
                'statement': statement_data
            })

        except Wallet.DoesNotExist:
            # หากไม่พบกระเป๋า, ให้ตอบกลับ JSON พร้อม error 404
            return JsonResponse({'error': 'Wallet not found'}, status=404)  # ทดสอบ: ตรวจสอบกรณีที่ไม่พบกระเป๋าและตอบกลับข้อผิดพลาดได้หรือไม่

    else:
        # หากไม่ได้เลือก wallet_id ให้แสดงรายการกระเป๋าทั้งหมดของผู้ใช้
        wallets = account.wallets.all()  # ทดสอบ: ตรวจสอบว่าแสดงรายการกระเป๋าทั้งหมดได้ถูกต้องเมื่อไม่มี wallet_id
        data = None  # ไม่มีข้อมูลเฉพาะที่จะต้องแสดง
        labels = None  # ไม่มี labels ที่จะแสดง

        # แสดงหน้ารายการกระเป๋าใน template analysis.html
        return render(request, 'analysis.html', {
            'wallets': wallets,
            'data': data,
            'labels': labels
        })

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
        wallet = Wallet.objects.get(id=request.POST.get('wallet')) 
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
        income_goal = float(request.POST.get('income_goal'))
        expense_goal = float(request.POST.get('expense_goal'))

        # ตรวจสอบว่าเป้าหมายเดือน/ปีนี้มีอยู่แล้วหรือไม่
        if Scope.objects.filter(wallet=wallet, month=month, year=year).exists():
            # เพิ่มข้อความแจ้งเตือน (หากมีอยู่แล้ว)
            return HttpResponse("ERROR, Can't create 2 scope with same month")

        # สร้างเป้าหมายใหม่
        scope = Scope(
            wallet=wallet,
            month=month,
            year=year,
            income_goal=income_goal,
            expense_goal=expense_goal
        )
        
        scope.save()

        return redirect(request.META.get('HTTP_REFERER', '/'))
    else:
        # ถ้าเป็น GET ก็แสดงแบบฟอร์ม
        return HttpResponse("ERROR, Can't create_scope")

def edit_scope(request, scope_id):
    if request.method == 'POST':
        scope = get_object_or_404(Scope, id=scope_id)
        scope.income_goal = request.POST.get('income_goal')
        scope.expense_goal = request.POST.get('expense_goal')
        scope.save()
        return redirect(request.META.get('HTTP_REFERER', '/'))

    return HttpResponse("ERROR, Can't edit_scope")

def delete_scope(request, scope_id):
    scope = get_object_or_404(Scope, id=scope_id)
    wallet_id = scope.wallet.id  # เก็บ wallet_id ก่อนลบ scope
    scope.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))

def create_mission(request):
    if request.method == 'POST':
        wallet_id = request.POST['wallet']
        mName = request.POST['mName']
        amount = request.POST['amount']
        dueDate = request.POST['dueDate']

        wallet = Wallet.objects.get(id=wallet_id)

        new_mission = Mission(
            wallet=wallet,
            mName=mName,
            amount=amount,
            dueDate=dueDate,
        )
        new_mission.save()
        messages.success(request, 'Goal ถูกสร้างสำเร็จแล้ว')
        return redirect('goal', wallet_id=new_mission.wallet.id)

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
        messages.success(request, 'Preset ถูกสร้างสำเร็จแล้ว')
        return redirect('main')

    wallets = Wallet.objects.all()
    return HttpResponse("ERROR, Can't create_preset")

def wallet_detail(request, id):
    return HttpResponse("This view is not yet implemented.")

def progression(request):
    account = request.user.account  # ดึง Account ของผู้ใช้ปัจจุบัน
    wallets = account.wallets.all()  # ดึงทุก wallet ที่ผู้ใช้งานมี
    
    # ดึงข้อมูลจำนวน Wallet, Statement, Preset สำหรับทุก wallet
    wallet_count = wallets.count()
    preset_count = sum(wallet.presets.count() for wallet in wallets)
    mission_count = sum(wallet.missions.count() for wallet in wallets)
    scope_count = sum(wallet.scopes.count() for wallet in wallets)
    mission_count = sum(wallet.missions.count() for wallet in wallets)

    total_income = sum(wallet.statements.filter(type='in').aggregate(total_income=models.Sum('amount'))['total_income'] or 0 for wallet in wallets)

    has_successful_mission = any(
        mission.is_successful() for wallet in wallets for mission in wallet.missions.all()
    )

    return render(request, 'progression.html', {
        'wallet_count': wallet_count,
        'preset_count': preset_count,
        'mission_count': mission_count,
        'scope_count': scope_count,
        'total_income': total_income,
        'has_successful_mission': has_successful_mission,
    })



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


