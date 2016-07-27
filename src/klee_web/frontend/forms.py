from django import forms
from frontend.models import User

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
    size_sym_in = forms.IntegerField(required=False, min_value=0)

    def clean(self):
        cleaned_data = super(SubmitJobForm, self).clean()
        if not cleaned_data.get("code") and not cleaned_data.get("file"):
            raise forms.ValidationError("You must provide either"
                                        " a code sample "
                                        "in the text box or a source code "
                                        "file to analyze.")


class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    error_messages = {
        'duplicate_username': "A user with that username already exists.",
        'password_mismatch': "The two password fields didn't match.",
    }
    email = forms.EmailField(required=True)
    username = forms.RegexField(
        label="Username", max_length=30, regex=r'^[\w.@+-]+$',
        help_text="Required. 30 characters or fewer. Letters, digits and "
                  "@/./+/-/_ only.",
        error_messages={
            'invalid': "This value may contain only letters, numbers and "
                       "@/./+/-/_ characters."})
    password1 = forms.CharField(label="Password",
                                widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput,
        help_text="Enter the same password as above, for verification.")

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            User._default_manager.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(
            self.error_messages['duplicate_username'],
            code='duplicate_username',
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangePasswordForm(forms.Form):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    error_messages = {
        'password_mismatch': "The two password fields didn't match.",
    }
    old_password = forms.CharField(
        label="Old Password",
        widget=forms.PasswordInput)
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput,
        help_text="Enter the same password as above, for verification.")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2
