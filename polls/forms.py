from django import forms
from django.forms import TextInput, Textarea
from django.forms.extras.widgets import SelectDateWidget

class PollForm(forms.Form):
  question = forms.CharField(widget=Textarea(attrs={'rows':'3'}))
  min_choices = forms.IntegerField(widget=TextInput(attrs={'size':'2'}))
  max_choices = forms.IntegerField(widget=TextInput(attrs={'size':'2'}))
  starts_date = forms.DateField(widget=SelectDateWidget())
  starts_time = forms.TimeField(widget=TextInput(attrs={'size':'2'}))
  ends_date = forms.DateField(widget=SelectDateWidget())
  ends_time = forms.TimeField(widget=TextInput(attrs={'size':'2'}))
  allowed_voters = forms.MultipleChoiceField([])
  
  def __init__(self,allowed_voters,*args,**kwrds):
    super(PollForm,self).__init__(*args,**kwrds)
    self.fields['allowed_voters'].choices = allowed_voters
  