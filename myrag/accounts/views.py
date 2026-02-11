

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.http import HttpResponse

def login_view(request):
    return HttpResponse("Login page (coming soon)")

def logout_view(request):
    logout(request)
    return redirect("/")










