from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import RegisterForm, LoginForm, AccountForm
from mainapp.models import Account

def auth(request):
    login_form = LoginForm()
    register_form = RegisterForm()
    account_form = AccountForm()
    show_register = False  

    if request.method == 'POST':
        if 'login' in request.POST:
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data['username']
                password = login_form.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('main')

        elif 'register' in request.POST:
            register_form = RegisterForm(request.POST)
            account_form = AccountForm(request.POST)
            show_register = True  

            if register_form.is_valid() and account_form.is_valid():
                user = register_form.save(commit=False)
                user.set_password(register_form.cleaned_data['password'])
                user.save()

                account = Account(
                    user=user,
                    name=account_form.cleaned_data['name'],
                    appTheme=account_form.cleaned_data['appTheme'],
                )
                account.save()

                messages.success(request, 'Registration successful. You can now log in.')
                return redirect('main')
            else:
                print(register_form.errors)
                messages.error(request, 'Registration failed. Please check the details.')

    context = {
        'login_form': login_form,
        'register_form': register_form,
        'account_form': account_form,
        'show_register': show_register,  
    }

    return render(request, 'registration/login_register.html', context)


