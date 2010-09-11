from django import forms
from captcha.fields import CaptchaField

class RegisterForm(forms.Form):
  keyfile = forms.FileField()
  captcha = CaptchaField()
  
class RenewForm(forms.Form):
  keyfile = forms.FileField()
  password = forms.CharField(widget=forms.PasswordInput)
  captcha = CaptchaField()
  
class LoginForm(forms.Form):
  username = forms.EmailField()
  password = forms.CharField(widget=forms.PasswordInput)
  