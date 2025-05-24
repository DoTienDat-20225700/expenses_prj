from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from .models import *
from .form import *
from django.contrib import messages
from django.contrib.auth import get_user

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  
            return redirect('ep1:ep1_lists')  
    else:
        form = RegisterForm()
    return render(request, 'ep1/register.html', {'form': form})

def create_default_categories(user):
    default_categories = [
        "Ăn uống",
        "Đi lại",
        "Nhà cửa",
        "Hóa đơn",
        "Mua sắm",
        "Giải trí",
        "Y tế",
        "Giáo dục",
        "Tiết kiệm",
        "Quà tặng"
    ]
    for cat_name in default_categories:
        Category.objects.get_or_create(name=cat_name, user=user)

@login_required
def profile(request):
    profile_obj, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST,  instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=profile_obj)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Cập nhật hồ sơ thành công!')
            return redirect('ep1:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile_obj)

    return render(request, 'ep1/profile.html', {
        'u_form': u_form,
        'p_form': p_form,
    })

from django.db.models import Sum
from .models import Expense, Category, Budget
from .form import ExpenseForm, RegisterForm, BudgetForm

@login_required
def ep1_lists(request):
    #Lấy danh sách chi tiêu của user
    expenses = Expense.objects.filter(user=request.user)

    #Tổng chi tiêu
    total_spent = expenses.aggregate(sum=Sum('amount'))['sum'] or 0

    #Danh mục chi nhiều nhất
    top = (expenses
           .values('category__name')
           .annotate(total=Sum('amount'))
           .order_by('-total')
           .first())
    top_category = top['category__name'] if top else '—'

    #Budget: get_or_create (mặc định total=0)
    budget_obj, _ = Budget.objects.get_or_create(user=request.user)

    #Xử lý BudgetForm khi user submit
    if request.method == 'POST' and 'budget_submit' in request.POST:
        b_form = BudgetForm(request.POST, instance=budget_obj)
        if b_form.is_valid():
            b_form.save()
            return redirect('ep1:ep1_lists')
    else:
        b_form = BudgetForm(instance=budget_obj)

    #Ngân sách còn lại = Budget.total – tổng đã chi
    remaining = budget_obj.total - total_spent

    return render(request, 'ep1/ep1_lists.html', {
        'expenses':      expenses,
        'total_spent':   total_spent,
        'top_category':  top_category,
        'remaining':     remaining,
        'b_form':        b_form,
        'budget_obj':    budget_obj,
    })

@login_required
def add_ep1(request):
    if not Category.objects.filter(user=request.user).exists():
        create_default_categories(request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = get_user(request) 
            expense.save()
            return redirect('ep1:ep1_lists')
    else:
        form = ExpenseForm(user=request.user)
    return render(request, 'ep1/add_ep1.html', {'form': form})

@login_required
def edit_ep1(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('ep1:ep1_lists')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    
    return render(request, 'ep1/edit_ep1.html', {'form': form})

@login_required
def delete_ep1(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
        return redirect('ep1:ep1_lists')
    
    return render(request, 'ep1/delete_ep1.html', {'expense': expense})