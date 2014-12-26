from django import forms

# Choices available for dropdowns.
num_choices = [(x, x) for x in xrange(0, 10)]


class SubmitJobForm(forms.Form):
    code = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    file = forms.FileField(required=False)
    args = forms.CharField(required=False)
    min_stdin_args = forms.ChoiceField(required=False, choices=num_choices)
    max_stdin_args = forms.ChoiceField(required=False, choices=num_choices)
    size_stdin_args = forms.IntegerField(required=False, min_value=0)
    num_files = forms.ChoiceField(required=False, choices=num_choices)
    size_files = forms.IntegerField(required=False, min_value=0)

    def clean(self):
        cleaned_data = super(SubmitJobForm, self).clean()
        if not cleaned_data.get("code") and not cleaned_data.get("file"):
            raise forms.ValidationError("You must provide either"
                                        " a code sample "
                                        "in the text box or a source code "
                                        "file to analyze.")
