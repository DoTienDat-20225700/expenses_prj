from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
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

User = get_user_model()

class UserLoginForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            # Kiểm tra xem user có tồn tại và password đúng không
            try:
                user = User.objects.get(username=username)
                
                # Nếu pass đúng NHƯNG tài khoản bị khóa (is_active=False)
                if user.check_password(password) and not user.is_active:
                    raise forms.ValidationError(
                        "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên để mở lại.",
                        code='inactive',
                    )
            except User.DoesNotExist:
                # Nếu user không tồn tại, cứ để mặc định Django xử lý lỗi chung
                pass
        
        # Gọi lại hàm cha để xử lý các lỗi đăng nhập thông thường
        return super().clean()

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
