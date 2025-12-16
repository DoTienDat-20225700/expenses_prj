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
            'total': forms.TextInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'style': 'width: 8rem;',  
                'min': '0',
                'step': '10000',
                'placeholder': '0'
            }),
        }
        labels = {
            'total': ''
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.total:
            self.initial['total'] = "{:,.0f}".format(self.instance.total)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nhập tên danh mục (Ví dụ: Tiền học, Đầu tư...)'
            }),
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
