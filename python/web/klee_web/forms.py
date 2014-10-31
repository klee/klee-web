from django import forms


class SubmitJobForm(forms.Form):
    code = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    file = forms.FileField(required=False)
    args = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super(SubmitJobForm, self).clean()
        if not cleaned_data.get("code") and not cleaned_data.get("file"):
            raise forms.ValidationError("You must provide either"
                                        " a code sample "
                                        "in the text box or a source code "
                                        "file to analyze.")
