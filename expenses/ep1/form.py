from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from .models import Budget


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['amount', 'description', 'category', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['total']
        widgets = {
            'total': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'style': 'width: 6rem;',  # điều chỉnh rộng vừa đủ
                'min': '0',
                'step': '1000',
                'placeholder': '0'
            }),
        }
        labels = {
            'total': ''
        }

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="Email",
        widget=forms.EmailInput(attrs={'class':'form-control'}))
    class Meta:
        model  = User
        fields = ['email']

class ProfileUpdateForm(forms.ModelForm):
    full_name     = forms.CharField(label="Họ tên",
        widget=forms.TextInput(attrs={'class':'form-control'}))
    date_of_birth = forms.DateField(label="Ngày sinh",
        widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    gender        = forms.ChoiceField(label="Giới tính",
        choices=Profile.GENDER_CHOICES,
        widget=forms.Select(attrs={'class':'form-control'}))
    hometown      = forms.CharField(label="Quê quán",
        widget=forms.TextInput(attrs={'class':'form-control'}))
    ethnicity     = forms.CharField(label="Dân tộc",
        widget=forms.TextInput(attrs={'class':'form-control'}))
    occupation    = forms.CharField(label="Nghề nghiệp",
        widget=forms.TextInput(attrs={'class':'form-control'}))

    class Meta:
        model  = Profile
        fields = ['full_name','date_of_birth','gender','hometown','ethnicity','occupation']
