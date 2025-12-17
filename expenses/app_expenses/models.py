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
    full_name     = models.CharField("Họ tên",      max_length=150, null=True, blank=True)
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

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
