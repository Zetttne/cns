from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Extended user profile with role and MSNV"""
    ROLE_CHOICES = [
        ('SUPERVISOR', 'Supervisor'),
        ('LEAD', 'Lead'),
        ('DATA_PROCESSOR', 'Data Processor'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    msnv = models.CharField(max_length=50, blank=True, null=True, verbose_name='Employee ID')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class Group(models.Model):
    """Work group/department"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        ordering = ['name']


class Batch(models.Model):
    """Batch/Phiếu to group multiple transfer requests"""
    batch_number = models.CharField(max_length=50, unique=True, verbose_name='Số phiếu')
    description = models.TextField(blank=True, null=True, verbose_name='Lý do chuyển đổi')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='batches_created', verbose_name='Người tạo')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Tạo lúc')
    designated_lead = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='batches_designated', verbose_name='Lead duyệt')
    
    def __str__(self):
        return f"Phiếu {self.batch_number}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'


class TransferRequest(models.Model):
    """Employee transfer request with approval workflow"""
    STATUS_CHOICES = [
        ('PENDING', 'Chờ duyệt'),
        ('APPROVED', 'Đã duyệt'),
        ('CONFIRMED', 'Đã xác nhận'),
        ('REJECTED', 'Từ chối'),
        ('CANCELED', 'Hủy'),
    ]

    batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='requests', verbose_name='Phiếu')
    msnv = models.CharField(max_length=50, verbose_name='MSNV')
    # Legacy foreign keys (optional display)
    from_group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name='transfers_from', null=True, blank=True)
    to_group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name='transfers_to', null=True, blank=True)
    # New 5-digit codes input by user
    from_code = models.CharField(max_length=5, verbose_name='Nhóm hiện tại', help_text='Mã nhóm 5 số', default='00000')
    to_code = models.CharField(max_length=5, verbose_name='Nhóm chuyển đến', help_text='Mã nhóm 5 số', default='00000')
    effective_date = models.DateField(verbose_name='Ngày hiệu lực')
    is_permanent = models.BooleanField(default=False, verbose_name='Chuyển cố định')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='Trạng thái')

    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='requests_created', verbose_name='Người yêu cầu')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests_approved', verbose_name='Người duyệt')
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests_confirmed', verbose_name='Người xác nhận')
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests_rejected', verbose_name='Người từ chối')
    canceled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests_canceled', verbose_name='Người hủy')

    rejection_reason = models.TextField(blank=True, null=True, verbose_name='Lý do từ chối')

    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Duyệt lúc')
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='Xác nhận lúc')
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name='Từ chối lúc')
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name='Hủy lúc')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Tạo lúc')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Cập nhật lúc')
    
    def __str__(self):
        return f"Chuyển #{self.id}: {self.msnv} ({self.status})"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transfer Request'
        verbose_name_plural = 'Transfer Requests'
