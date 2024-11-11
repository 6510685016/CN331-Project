import json
from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import UserRegisterForm, AccountForm
from mainapp.models import Account
from django.contrib.auth.models import User

def register(request):
    if request.method == "POST":
        user_form = UserRegisterForm(request.POST)
        account_form = AccountForm(request.POST, request.FILES)  

        if user_form.is_valid() and account_form.is_valid():
            user = user_form.save()  
            login(request, user)  

            profile_pic = account_form.cleaned_data.get('profile_pic') 
            if not profile_pic:  # ถ้าไม่มีการอัปโหลดไฟล์
                profile_pic = 'media/profile_photos/default.jpg'

            # บันทึกข้อมูลบัญชี
            account = Account(
                user=user,
                name=account_form.cleaned_data['name'],
                appTheme=account_form.cleaned_data['appTheme'],
                profile_pic=profile_pic, 
            )

            try:
                account.save() 
            except Exception as e:
                print(f"Error saving Account: {e}")  

            return redirect('main')
    else:
        user_form = UserRegisterForm()
        account_form = AccountForm()

    context = {
        "user_form": user_form,
        "account_form": account_form,
    }
    return render(request, 'registration/register.html', context)
