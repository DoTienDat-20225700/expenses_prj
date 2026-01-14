from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên danh mục")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người dùng")
    
    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"
    
    def __str__(self):
        return self.name

class Expense(models.Model):
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        verbose_name="Số tiền"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Mô tả"
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Danh mục"
    )
    date = models.DateField(verbose_name="Ngày chi tiêu")
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name="Người dùng"
    )
    
    class Meta:
        verbose_name = "Chi tiêu"
        verbose_name_plural = "Chi tiêu"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.amount} - {self.category} - {self.date}"
    

class Budget(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Người dùng")
    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Ngân sách"
    )

    class Meta:
        verbose_name = "Ngân sách"
        verbose_name_plural = "Ngân sách"

    def __str__(self):
        return f"{self.user.username}: {self.total}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField("Ảnh đại diện", upload_to='avatars/', default='avatars/default.png', blank=True)
    full_name = models.CharField("Họ tên",  max_length=150, null=True, blank=True)
    date_of_birth = models.DateField("Ngày sinh",   null=True, blank=True)
    GENDER_CHOICES = [
        ('M','Nam'),
        ('F','Nữ'),
        ('O','Khác'),
    ]
    gender        = models.CharField("Giới tính",   max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    hometown      = models.CharField("Quê quán",    max_length=255, null=True, blank=True)
    ethnicity     = models.CharField("Dân tộc",     max_length=100, null=True, blank=True)
    occupation    = models.CharField("Nghề nghiệp", max_length=100, null=True, blank=True)

    def __str__(self):
        return self.user.username
    
class Announcement(models.Model):
    TYPE_CHOICES = [
        ('info', 'Thông tin (Xanh dương)'),
        ('success', 'Thành công (Xanh lá)'),
        ('warning', 'Cảnh báo (Vàng)'),
        ('danger', 'Khẩn cấp (Đỏ)'),
    ]
    
    title = models.CharField("Tiêu đề", max_length=200)
    content = models.TextField("Nội dung")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    is_active = models.BooleanField("Hiển thị", default=True)
    priority = models.CharField("Loại thông báo", max_length=10, choices=TYPE_CHOICES, default='info')

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']

class RecurringExpense(models.Model):
    """
    Mẫu định kỳ để tự động tạo chi tiêu lặp lại.
    
    Cách hoạt động:
    1. Tạo mẫu với start_date và frequency
    2. Hệ thống tự động tính next_due_date (ngày tạo chi tiêu lần sau)
    3. Khi next_due_date <= hôm nay, nhấn "Tạo Chi Tiêu" để tạo expense thực
    4. Sau khi tạo, next_due_date tự động tăng lên 1 khoảng (theo frequency)
    5. Lặp lại bước 3-4
    
    Ví dụ:
        Tiền điện hàng tháng:
        - start_date = 15/01/2026
        - frequency = 'monthly'
        - next_due_date = 15/01/2026 (lần đầu)
        
        Sau khi tạo chi tiêu:
        - next_due_date = 15/02/2026 (tự động tăng)
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Hàng ngày'),
        ('weekly', 'Hàng tuần'),
        ('monthly', 'Hàng tháng'),
        ('yearly', 'Hàng năm'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người dùng")
    name = models.CharField("Tên chi tiêu", max_length=200)
    amount = models.DecimalField("Số tiền", max_digits=15, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Danh mục")
    frequency = models.CharField("Tần suất", max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    
    # Ngày bắt đầu: Mốc gốc, xác định ngày nào trong tháng/tuần
    # VD: start_date = 15/01 → Tạo vào ngày 15 mỗi tháng
    start_date = models.DateField("Ngày bắt đầu")
    
    # Ngày kết thúc: Ngày MẪU hết hạn (không bắt buộc)
    # VD: end_date = 30/06 → Sau 30/06 mẫu tự động tắt
    end_date = models.DateField("Ngày kết thúc", null=True, blank=True)
    
    # Ngày đến hạn tiếp theo: Ngày CỤ THỂ sẽ tạo chi tiêu lần sau
    # VD: next_due_date = 15/02/2026 → Tạo chi tiêu vào 15/02
    # Field này TỰ ĐỘNG cập nhật, user KHÔNG nhập
    next_due_date = models.DateField("Ngày đến hạn tiếp theo")
    
    is_active = models.BooleanField("Đang hoạt động", default=True)
    description = models.TextField("Ghi chú", blank=True, null=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    
    class Meta:
        verbose_name = "Chi tiêu định kỳ"
        verbose_name_plural = "Chi tiêu định kỳ"
        ordering = ['-next_due_date']
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"
    
    def calculate_next_occurrence(self, from_date=None):
        """
        Tính ngày đến hạn tiếp theo dựa trên start_date và frequency.
        
        Args:
            from_date (date, optional): Ngày tính từ đó (mặc định = hôm nay)
        
        Returns:
            date: Ngày đến hạn tiếp theo (>= from_date)
        
        Example:
            recurring = RecurringExpense(start_date='2026-01-10', frequency='monthly')
            next_date = recurring.calculate_next_occurrence()  # 2026-02-10 nếu hôm nay > 10/01
        """
        from .utils.recurring_utils import calculate_next_due_date
        from django.utils import timezone
        
        if from_date is None:
            from_date = timezone.now().date()
        
        return calculate_next_due_date(self.start_date, self.frequency, from_date)
    
    def is_due_today(self):
        """
        Kiểm tra xem mẫu này có đến hạn hôm nay không.
        
        Returns:
            bool: True nếu next_due_date <= hôm nay
        
        Example:
            if recurring.is_due_today():
                print("Đã đến hạn! Có thể tạo chi tiêu.")
        """
        from django.utils import timezone
        today = timezone.now().date()
        return self.next_due_date <= today
    
    def is_expired(self):
        """
        Kiểm tra xem mẫu này đã hết hạn chưa (dựa trên end_date).
        
        Returns:
            bool: True nếu đã quá end_date
        
        Example:
            if recurring.is_expired():
                recurring.is_active = False
                recurring.save()
        """
        if not self.end_date:
            return False
        
        from django.utils import timezone
        today = timezone.now().date()
        return today > self.end_date
    
    def advance_next_due_date(self):
        """
        Tăng next_due_date lên 1 khoảng theo frequency.
        
        Hàm này được gọi SAU KHI tạo chi tiêu thực từ mẫu.
        
        Example:
            # Trước: next_due_date = 15/01/2026
            recurring.advance_next_due_date()
            # Sau: next_due_date = 15/02/2026 (nếu frequency='monthly')
        """
        from .utils.recurring_utils import add_frequency_to_date
        self.next_due_date = add_frequency_to_date(self.next_due_date, self.frequency)



class IncomeSource(models.Model):
    name = models.CharField("Tên nguồn thu", max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người dùng")
    
    class Meta:
        verbose_name = "Nguồn thu nhập"
        verbose_name_plural = "Nguồn thu nhập"
    
    def __str__(self):
        return self.name


class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người dùng")
    amount = models.DecimalField("Số tiền", max_digits=15, decimal_places=2)
    source = models.ForeignKey(IncomeSource, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Nguồn thu")
    description = models.TextField("Mô tả", blank=True, null=True)
    date = models.DateField("Ngày thu")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    
    class Meta:
        verbose_name = "Thu nhập"
        verbose_name_plural = "Thu nhập"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.amount} - {self.source} - {self.date}"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        # Tạo danh mục chi tiêu mặc định
        default_categories = [
            "Ăn uống", "Đi lại", "Nhà cửa", "Hóa đơn", "Mua sắm",
            "Giải trí", "Y tế", "Giáo dục", "Tiết kiệm", "Quà tặng"
        ]
        for cat_name in default_categories:
            Category.objects.create(name=cat_name, user=instance)
        
        # Tạo nguồn thu nhập mặc định
        default_income_sources = [
            "Lương", "Thưởng", "Freelance", "Đầu tư", "Kinh doanh", "Khác"
        ]
        for source_name in default_income_sources:
            IncomeSource.objects.create(name=source_name, user=instance)
    instance.profile.save()
