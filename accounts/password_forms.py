from django import forms

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

class VerifyCodeForm(forms.Form):
    email = forms.EmailField()
    code = forms.CharField(max_length=6)

class ResetPasswordForm(forms.Form):
    email = forms.EmailField()
    code = forms.CharField(max_length=6)
    new_password1 = forms.CharField(widget=forms.PasswordInput)
    new_password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", "Passwords do not match.")
        return cleaned
