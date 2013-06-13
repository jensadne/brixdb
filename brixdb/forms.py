from django import forms


class SimpleIntegerForm(forms.Form):
    number = forms.IntegerField()
