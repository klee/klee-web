from django import forms


class AdminConfigForm(forms.Form):
    timeout = forms.IntegerField(min_value=0, required=False)
    cpu_share = forms.IntegerField(min_value=1, max_value=100, required=False)
    memory_limit = forms.IntegerField(min_value=0, max_value=8192,
                                      required=False)
