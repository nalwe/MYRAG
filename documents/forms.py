# documents/forms.py
from django import forms
from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["file"]  # 👈 DO NOT include owner, is_public, folder

