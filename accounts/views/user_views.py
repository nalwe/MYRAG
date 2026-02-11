from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth.models import User

from accounts.models import Profile, Organization


@login_required
def create_user(request):
    """
    Create a company user, assign role and tier
    """

    # Only org admins or superusers can create users
    member = OrganizationMember.objects.filter(user=request.user).first()
    if not (request.user.is_superuser or (member and member.is_admin())):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "")
        role = request.POST.get("role")        # member | admin
        tier = request.POST.get("tier")        # basic | premium

        if not username or not password:
            return render(
                request,
                "accounts/create_user.html",
                {"error": "Username and password are required."}
            )

        if User.objects.filter(username=username).exists():
            return render(
                request,
                "accounts/create_user.html",
                {"error": "A user with this username already exists."}
            )

        # Create user
        user = User.objects.create_user(
            username=username,
            password=password
        )

        # Create profile (if not auto via signal)
        Profile.objects.get_or_create(
            user=user,
            defaults={
                "is_active": True,
                "is_suspended": False,
            }
        )

        # Assign organization + role + tier
        OrganizationMember.objects.create(
            user=user,
            organization=member.organization,  # same company as creator
            role=role,
            tier=tier,
        )

        messages.success(request, "User created successfully.")
        return redirect("users_list")  # keep your existing flow

    return render(request, "accounts/create_user.html")
