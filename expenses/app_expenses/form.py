from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.models import User
from .models import Budget, Profile

class CustomClearableFileInput(forms.ClearableFileInput):
    template_name = 'django/forms/widgets/file.html'

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
    avatar        = forms.ImageField(label="Ảnh đại diện", required=False, widget=CustomClearableFileInput(attrs={'style': 'display:none;'}))

    full_name     = forms.CharField(label="Họ tên",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ và tên'}))
    
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
        fields = ['avatar', 'full_name', 'date_of_birth', 'gender', 'hometown', 'ethnicity', 'occupation']


class RecurringExpenseForm(forms.ModelForm):
    class Meta:
        model = RecurringExpense
        fields = ['name', 'amount', 'category', 'frequency', 'start_date', 'end_date', 'next_due_date', 'description', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'next_due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Tiền điện hàng tháng'}),
            'amount': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 1,000,000'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)
        
        # Make end_date and next_due_date optional
        self.fields['end_date'].required = False
        self.fields['next_due_date'].required = False
        
        # next_due_date visual styling (not readonly to allow submission)
        self.fields['next_due_date'].widget.attrs['class'] = 'form-control bg-light'
        self.fields['next_due_date'].help_text = 'Tự động tính toán bởi hệ thống'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Only validate if both dates are provided
        if start_date and end_date:
            # Rule 1: Ngày bắt đầu phải < ngày kết thúc
            if start_date >= end_date:
                raise forms.ValidationError(
                    'Ngày kết thúc phải lớn hơn ngày bắt đầu.'
                )
            
            # Rule 2: Ngày kết thúc phải > ngày đến hạn
            # For new records, next_due_date will be set to start_date
            # For existing records, check against current next_due_date
            if self.instance and self.instance.pk and self.instance.next_due_date:
                if end_date <= self.instance.next_due_date:
                    raise forms.ValidationError(
                        f'Ngày kết thúc phải lớn hơn ngày đến hạn tiếp theo ({self.instance.next_due_date.strftime("%d/%m/%Y")}).'
                    )
            else:
                # For new records, next_due_date will be start_date
                # So end_date must be > start_date (already checked above)
                pass
        
        return cleaned_data



class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['amount', 'source', 'description', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 1,000,000'}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mô tả nguồn thu...'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['source'].queryset = IncomeSource.objects.filter(user=user)


class IncomeSourceForm(forms.ModelForm):
    class Meta:
        model = IncomeSource
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nhập tên nguồn thu (VD: Lương, Freelance...)'
            }),
        }