from django import forms
from .models import AbsenceJustification

class JustificationForm(forms.ModelForm):
    class Meta:
        model = AbsenceJustification
        fields = ['document']
        widgets = {
            'document': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
        }
