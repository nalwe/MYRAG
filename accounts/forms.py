from django import forms
from django.contrib.auth.models import User
from accounts.models import Organization
from accounts.models import Profile


ROLE_CHOICES = (
    ("admin", "Admin"),
    ("premium", "Premium"),
    ("basic", "Basic"),
)


class CreateUserForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Password"
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="Role"
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label="Company"
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError(
                "A user with this email already exists."
            )
        return email
    




class OrgUserCreateForm(forms.Form):
    email = forms.EmailField()
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)

