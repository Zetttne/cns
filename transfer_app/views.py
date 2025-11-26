from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
import uuid
from .models import UserProfile, Group, TransferRequest, Batch


def get_profile(user):
    return getattr(user, 'profile', None)

def role_required(*roles):
    def decorator(fn):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('transfer_app:login')
            profile = get_profile(request.user)
            if not profile or profile.role not in roles:
                messages.error(request, 'Permission denied')
                return redirect('transfer_app:dashboard')
            return fn(request, *args, **kwargs)
        return wrapper
    return decorator

def api_debug(request):
    return HttpResponse('Running in pure Django mode (no external API).', content_type='text/plain')


def index(request):
    if request.user.is_authenticated:
        return redirect('transfer_app:dashboard')
    return redirect('transfer_app:login')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('transfer_app:dashboard')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'transfer_app/login.html')


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')
        role = request.POST.get('role')
        msnv = request.POST.get('msnv')
        if not username or not password or not role:
            messages.error(request, 'Username, password and role are required')
        elif password != confirm:
            messages.error(request, 'Passwords do not match')
        elif role not in ['SUPERVISOR', 'LEAD', 'DATA_PROCESSOR']:
            messages.error(request, 'Invalid role')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            user = User.objects.create_user(username=username, password=password)
            UserProfile.objects.create(user=user, role=role, msnv=msnv)
            messages.success(request, 'Registration successful! Please login.')
            return redirect('transfer_app:login')
    return render(request, 'transfer_app/register.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('transfer_app:login')


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('transfer_app:login')

    # --- Filters ---
    desc_query = request.GET.get('desc', '').strip()
    status_query = request.GET.get('status', '').strip()
    created_from = request.GET.get('created_from', '').strip()
    created_to = request.GET.get('created_to', '').strip()
    approved_query = request.GET.get('approved_by', '').strip()
    confirmed_query = request.GET.get('confirmed_by', '').strip()
    requested_query = request.GET.get('requested_by', '').strip()
    msnv_query = request.GET.get('msnv', '').strip()
    page = request.GET.get('page', '1')
    try:
        page_num = int(page)
    except ValueError:
        page_num = 1
    page_size = request.GET.get('page_size', '20')
    try:
        page_size_num = int(page_size)
        if page_size_num not in [10,20,50,100]:
            page_size_num = 20
    except ValueError:
        page_size_num = 20

    qs = TransferRequest.objects.select_related(
        'batch','to_group','from_group','requested_by','approved_by','confirmed_by'
    ).all().order_by('-created_at')

    if desc_query:
        qs = qs.filter(Q(batch__description__icontains=desc_query))
    if status_query:
        qs = qs.filter(status=status_query)
    # Date range (created_at)
    if created_from:
        try:
            qs = qs.filter(created_at__date__gte=created_from)
        except Exception:
            pass
    if created_to:
        try:
            qs = qs.filter(created_at__date__lte=created_to)
        except Exception:
            pass
    if approved_query:
        qs = qs.filter(
            Q(approved_by__username__icontains=approved_query) |
            Q(approved_by__profile__msnv__icontains=approved_query)
        )
    if confirmed_query:
        qs = qs.filter(
            Q(confirmed_by__username__icontains=confirmed_query) |
            Q(confirmed_by__profile__msnv__icontains=confirmed_query)
        )
    if requested_query:
        qs = qs.filter(
            Q(requested_by__username__icontains=requested_query) |
            Q(requested_by__profile__msnv__icontains=requested_query)
        )
    if msnv_query:
        qs = qs.filter(msnv__icontains=msnv_query)

    total_rows = qs.count()
    paginator = Paginator(qs, page_size_num)
    page_obj = paginator.get_page(page_num)

    # Group only visible page requests
    batches = {}
    standalone = []
    for tr in page_obj.object_list:
        if tr.batch:
            if tr.batch.id not in batches:
                batches[tr.batch.id] = {
                    'batch': tr.batch,
                    'requests': []
                }
            batches[tr.batch.id]['requests'].append(tr)
        else:
            standalone.append(tr)

    # Role specific sections
    profile = get_profile(request.user)
    my_requests = approved_by_me = confirmed_by_me = []
    if profile:
        if profile.role == 'SUPERVISOR':
            my_requests = TransferRequest.objects.filter(requested_by=request.user).order_by('-created_at')[:20]
        elif profile.role == 'LEAD':
            approved_by_me = TransferRequest.objects.filter(approved_by=request.user).order_by('-approved_at')[:20]
        elif profile.role == 'DATA_PROCESSOR':
            confirmed_by_me = TransferRequest.objects.filter(confirmed_by=request.user).order_by('-confirmed_at')[:20]

    status_choices = [
        ('PENDING', 'Chờ duyệt'),
        ('APPROVED', 'Đã duyệt'),
        ('CONFIRMED', 'Đã xác nhận'),
        ('REJECTED', 'Từ chối'),
        ('CANCELED', 'Hủy'),
    ]
    page_size_options = [10, 20, 50, 100]

    # Distinct usernames for approved/confirmed filters (for select options)
    approved_usernames = list(
        TransferRequest.objects.filter(approved_by__isnull=False)
        .order_by('approved_by__username')
        .values_list('approved_by__username', flat=True)
        .distinct()
    )
    confirmed_usernames = list(
        TransferRequest.objects.filter(confirmed_by__isnull=False)
        .order_by('confirmed_by__username')
        .values_list('confirmed_by__username', flat=True)
        .distinct()
    )
    
    context = {
        'batches': list(batches.values()),
        'standalone': standalone,
        'user': request.user,
        'page_obj': page_obj,
        'page_size': page_size_num,
        'total_rows': total_rows,
        'desc_query': desc_query,
        'status_query': status_query,
        'created_from': created_from,
        'created_to': created_to,
        'approved_query': approved_query,
        'confirmed_query': confirmed_query,
        'requested_query': requested_query,
        'msnv_query': msnv_query,
        'my_requests': my_requests,
        'approved_by_me': approved_by_me,
        'confirmed_by_me': confirmed_by_me,
        'paginator': paginator,
        'status_choices': status_choices,
        'page_size_options': page_size_options,
        'approved_usernames': approved_usernames,
        'confirmed_usernames': confirmed_usernames,
    }
    return render(request, 'transfer_app/dashboard.html', context)


@login_required
def my_requests_full(request):
    profile = get_profile(request.user)
    if not profile or profile.role != 'SUPERVISOR':
        messages.error(request, 'Chỉ Supervisor mới xem toàn bộ yêu cầu đã tạo')
        return redirect('transfer_app:dashboard')
    qs = TransferRequest.objects.filter(requested_by=request.user).order_by('-created_at')
    page_num = int(request.GET.get('page', '1')) if request.GET.get('page', '1').isdigit() else 1
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(page_num)
    return render(request, 'transfer_app/list_full.html', {
        'title': 'Yêu cầu của tôi',
        'mode': 'created',
        'page_obj': page_obj,
        'user': request.user,
    })


@login_required
def approved_by_me_full(request):
    profile = get_profile(request.user)
    if not profile or profile.role != 'LEAD':
        messages.error(request, 'Chỉ Lead mới xem toàn bộ yêu cầu đã duyệt')
        return redirect('transfer_app:dashboard')
    qs = TransferRequest.objects.filter(approved_by=request.user).order_by('-approved_at')
    page_num = int(request.GET.get('page', '1')) if request.GET.get('page', '1').isdigit() else 1
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(page_num)
    return render(request, 'transfer_app/list_full.html', {
        'title': 'Tôi đã duyệt',
        'mode': 'approved',
        'page_obj': page_obj,
        'user': request.user,
    })


@login_required
def confirmed_by_me_full(request):
    profile = get_profile(request.user)
    if not profile or profile.role != 'DATA_PROCESSOR':
        messages.error(request, 'Chỉ Data Processor mới xem toàn bộ yêu cầu đã xác nhận')
        return redirect('transfer_app:dashboard')
    qs = TransferRequest.objects.filter(confirmed_by=request.user).order_by('-confirmed_at')
    page_num = int(request.GET.get('page', '1')) if request.GET.get('page', '1').isdigit() else 1
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(page_num)
    return render(request, 'transfer_app/list_full.html', {
        'title': 'Tôi đã xác nhận',
        'mode': 'confirmed',
        'page_obj': page_obj,
        'user': request.user,
    })


def view_request(request, request_id):
    if not request.user.is_authenticated:
        return redirect('transfer_app:login')
    transfer = get_object_or_404(
        TransferRequest.objects.select_related(
            'from_group', 'to_group', 'requested_by', 'approved_by', 'confirmed_by'
        ),
        id=request_id
    )
    return render(request, 'transfer_app/view_request.html', {
        'user': request.user,
        'request_data': transfer
    })


@role_required('SUPERVISOR')
def create_request(request):
    if request.method == 'POST':
        msnv_input = request.POST.get('msnv', '').strip()
        from_code = request.POST.get('from_code', '').strip()
        to_code = request.POST.get('to_code', '').strip()
        effective_date = request.POST.get('effective_date')
        is_permanent = request.POST.get('is_permanent') == 'on'
        batch_desc = request.POST.get('batch_description', '').strip()
        designated_lead_id = request.POST.get('designated_lead')

        def valid_code(c):
            return len(c) == 5 and c.isdigit()

        # Parse multiple MSNVs (comma, space, or newline separated)
        msnv_list = [m.strip() for m in msnv_input.replace('\n', ' ').replace(',', ' ').replace(';', ' ').split() if m.strip()]
        
        if not msnv_list:
            messages.error(request, 'Vui lòng nhập ít nhất một MSNV')
        elif not all([from_code, to_code, effective_date, designated_lead_id]):
            messages.error(request, 'Tất cả các trường đều bắt buộc (bao gồm Người duyệt)')
        elif from_code == to_code:
            messages.error(request, 'Mã nhóm hiện tại và chuyển đến phải khác nhau')
        elif not valid_code(from_code) or not valid_code(to_code):
            messages.error(request, 'Mã nhóm phải gồm đúng 5 chữ số')
        else:
            try:
                with transaction.atomic():
                    # Validate designated lead
                    try:
                        designated_lead = User.objects.get(id=designated_lead_id)
                        lead_profile = get_profile(designated_lead)
                        if not lead_profile or lead_profile.role != 'LEAD':
                            messages.error(request, 'Người duyệt phải là tài khoản LEAD hợp lệ')
                            raise ValueError('Invalid lead')
                    except Exception:
                        raise ValueError('Lead không tồn tại')
                    # Always create a batch (phiếu) even for single MSNV
                    last_batch = Batch.objects.order_by('-id').first()
                    next_id = (last_batch.id + 1) if last_batch else 1
                    batch_number = f"PH{next_id:05d}"
                    auto_desc = f"Chuyển {len(msnv_list)} MSNV từ {from_code} sang {to_code}"
                    batch = Batch.objects.create(
                        batch_number=batch_number,
                        description=batch_desc or auto_desc,
                        created_by=request.user,
                        designated_lead=designated_lead
                    )
                    
                    # Create requests for each MSNV
                    requests_created = []
                    for msnv in msnv_list:
                        tr = TransferRequest.objects.create(
                            batch=batch,
                            msnv=msnv,
                            from_code=from_code,
                            to_code=to_code,
                            effective_date=effective_date,
                            is_permanent=is_permanent,
                            requested_by=request.user
                        )
                        requests_created.append(tr)
                    
                    messages.success(request, f'Đã tạo phiếu {batch.batch_number} với {len(requests_created)} yêu cầu. Lead duyệt: {designated_lead.username}')
                    return redirect('transfer_app:dashboard')
            except Exception as e:
                messages.error(request, f'Lỗi tạo yêu cầu: {e}')
    # Provide leads list
    leads = User.objects.filter(profile__role='LEAD').order_by('username')
    return render(request, 'transfer_app/create_request.html', {'user': request.user, 'leads': leads})


@role_required('LEAD')
def approve_request(request, request_id):
    if request.method != 'POST':
        return redirect('transfer_app:view_request', request_id=request_id)
    tr = get_object_or_404(TransferRequest, id=request_id)
    # Restrict to designated lead if set
    if tr.batch and tr.batch.designated_lead and tr.batch.designated_lead != request.user:
        messages.error(request, 'Bạn không phải Lead được chỉ định cho phiếu này')
    elif tr.status != 'PENDING':
        messages.error(request, f'Request is already {tr.status.lower()}')
    else:
        tr.approved_by = request.user
        tr.approved_at = timezone.now()
        tr.status = 'APPROVED'
        tr.save()
        messages.success(request, f'Request #{request_id} approved successfully')
    return redirect('transfer_app:view_request', request_id=request_id)


@role_required('DATA_PROCESSOR')
def confirm_request(request, request_id):
    if request.method != 'POST':
        return redirect('transfer_app:view_request', request_id=request_id)
    tr = get_object_or_404(TransferRequest, id=request_id)
    if tr.status != 'APPROVED':
        messages.error(request, 'Only approved requests can be confirmed')
    else:
        tr.confirmed_by = request.user
        tr.confirmed_at = timezone.now()
        tr.status = 'CONFIRMED'
        tr.save()
        messages.success(request, f'Request #{request_id} confirmed and completed')
    return redirect('transfer_app:view_request', request_id=request_id)


@role_required('LEAD', 'DATA_PROCESSOR')
def reject_request(request, request_id):
    if request.method != 'POST':
        return redirect('transfer_app:view_request', request_id=request_id)
    tr = get_object_or_404(TransferRequest, id=request_id)
    profile = get_profile(request.user)
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Rejection reason is required')
        return redirect('transfer_app:view_request', request_id=request_id)
    
    # DATA_PROCESSOR can only reject APPROVED requests
    if profile.role == 'DATA_PROCESSOR' and tr.status != 'APPROVED':
        messages.error(request, 'Data Processor chỉ có thể từ chối yêu cầu đã được duyệt')
        return redirect('transfer_app:view_request', request_id=request_id)
    
    # LEAD can reject PENDING requests
    if profile.role == 'LEAD' and tr.status != 'PENDING':
        messages.error(request, 'Lead chỉ có thể từ chối yêu cầu đang chờ duyệt')
        return redirect('transfer_app:view_request', request_id=request_id)
    
    if tr.status in ['CONFIRMED', 'REJECTED', 'CANCELED']:
        messages.error(request, f'Request is already {tr.status.lower()}')
    else:
        tr.status = 'REJECTED'
        tr.rejection_reason = reason
        tr.rejected_by = request.user
        tr.rejected_at = timezone.now()
        tr.save()
        messages.success(request, f'Request #{request_id} rejected')
    return redirect('transfer_app:view_request', request_id=request_id)

@role_required('SUPERVISOR')
def cancel_request(request, request_id):
    if request.method != 'POST':
        return redirect('transfer_app:view_request', request_id=request_id)
    tr = get_object_or_404(TransferRequest, id=request_id)
    if tr.requested_by != request.user:
        messages.error(request, 'Chỉ người tạo mới được hủy phiếu này')
    elif tr.status != 'PENDING':
        messages.error(request, 'Chỉ hủy được yêu cầu đang chờ duyệt')
    else:
        tr.status = 'CANCELED'
        tr.canceled_by = request.user
        tr.canceled_at = timezone.now()
        tr.save()
        messages.success(request, f'Đã hủy yêu cầu #{request_id}')
    return redirect('transfer_app:view_request', request_id=request_id)


@login_required
def bulk_action(request):
    if request.method != 'POST':
        return redirect('transfer_app:dashboard')
    action = request.POST.get('action')
    ids = request.POST.getlist('ids')
    reason = request.POST.get('reason', '').strip()
    if not ids:
        messages.error(request, 'Không có yêu cầu nào được chọn')
        return redirect('transfer_app:dashboard')
    profile = get_profile(request.user)
    success = 0
    skipped = 0
    skip_reasons = []
    success_reasons = []
    with transaction.atomic():
        for rid in ids:
            try:
                tr = TransferRequest.objects.select_for_update().get(id=rid)
            except TransferRequest.DoesNotExist:
                skipped += 1
                skip_reasons.append(f'Yêu cầu #{rid}: Không tồn tại')
                continue
            
            if action == 'approve':
                if profile.role != 'LEAD':
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Chỉ Lead mới được duyệt')
                elif tr.batch and tr.batch.designated_lead and tr.batch.designated_lead != request.user:
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id}: Lead không được chỉ định (phiếu yêu cầu: {tr.batch.designated_lead.username})')
                elif tr.status != 'PENDING':
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Trạng thái không phải "Chờ duyệt" (hiện tại: {tr.get_status_display()})')
                else:
                    tr.approved_by = request.user
                    tr.approved_at = timezone.now()
                    tr.status = 'APPROVED'
                    tr.save()
                    success += 1
                    success_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Đã duyệt thành công')
            elif action == 'confirm':
                if profile.role != 'DATA_PROCESSOR':
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Chỉ Data Processor mới được xác nhận')
                elif tr.status != 'APPROVED':
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Chỉ xác nhận được yêu cầu đã duyệt (hiện tại: {tr.get_status_display()})')
                else:
                    tr.confirmed_by = request.user
                    tr.confirmed_at = timezone.now()
                    tr.status = 'CONFIRMED'
                    tr.save()
                    success += 1
                    success_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Đã xác nhận thành công')
            elif action == 'reject':
                # DATA_PROCESSOR can only reject APPROVED, LEAD can only reject PENDING
                if profile.role == 'DATA_PROCESSOR' and tr.status != 'APPROVED':
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Data Processor chỉ từ chối được yêu cầu đã duyệt (hiện tại: {tr.get_status_display()})')
                elif profile.role == 'LEAD' and tr.status != 'PENDING':
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Lead chỉ từ chối được yêu cầu chờ duyệt (hiện tại: {tr.get_status_display()})')
                elif profile.role not in ['LEAD', 'DATA_PROCESSOR']:
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Không có quyền từ chối')
                elif tr.status in ['CONFIRMED', 'REJECTED', 'CANCELED']:
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Đã hoàn tất hoặc từ chối/hủy rồi')
                elif not reason:
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Thiếu lý do từ chối')
                else:
                    tr.status = 'REJECTED'
                    tr.rejection_reason = reason
                    tr.rejected_by = request.user
                    tr.rejected_at = timezone.now()
                    tr.save()
                    success += 1
                    success_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Đã từ chối - {reason}')
            elif action == 'cancel':
                if profile.role != 'SUPERVISOR':
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Chỉ Supervisor mới được hủy')
                elif tr.requested_by != request.user:
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id}: Không phải người tạo phiếu nên không thể hủy')
                elif tr.status != 'PENDING':
                    skipped += 1
                    skip_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Chỉ hủy được yêu cầu chờ duyệt (hiện tại: {tr.get_status_display()})')
                else:
                    tr.status = 'CANCELED'
                    tr.canceled_by = request.user
                    tr.canceled_at = timezone.now()
                    tr.save()
                    success += 1
                    success_reasons.append(f'Yêu cầu #{tr.id} (MSNV: {tr.msnv}): Đã hủy thành công')
            else:
                messages.error(request, 'Hành động không hợp lệ')
                return redirect('transfer_app:dashboard')
    
    if action == 'reject' and not reason:
        messages.error(request, 'Lý do từ chối bắt buộc')
    else:
        if success:
            messages.success(request, f'✓ {success} yêu cầu xử lý thành công:')
            for success_msg in success_reasons[:10]:  # Show first 10 success details
                messages.success(request, success_msg)
            if len(success_reasons) > 10:
                messages.success(request, f'... và {len(success_reasons) - 10} yêu cầu khác')
        if skipped:
            messages.warning(request, f'⚠ {skipped} yêu cầu bị bỏ qua:')
            for skip_msg in skip_reasons[:10]:  # Show first 10 reasons
                messages.info(request, skip_msg)
            if len(skip_reasons) > 10:
                messages.info(request, f'... và {len(skip_reasons) - 10} lý do khác')
    return redirect('transfer_app:dashboard')
