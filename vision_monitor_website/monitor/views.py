from django.shortcuts import render

def home(request):
    return render(request, 'monitor/home.html')

def monitor(request):
    # Add your LLM interaction logic here
    return render(request, 'monitor/monitor.html')