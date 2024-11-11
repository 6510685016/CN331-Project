from django.shortcuts import render

# Create your views here.

def login(request):
    return render(request, 'login.html')

def main(request):
    return render(request, 'main.html')

def about(request):
    return render(request, 'about.html')

def analysis(request):
    data = [10, 20, 30, 40, 50]
    labels = ["A", "B", "C", "D", "E"]

    return render(request, 'analysis.html', {'data': data, 'labels': labels})