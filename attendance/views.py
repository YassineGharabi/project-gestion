from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import AbsencePresence, Seance, Student
# Aliases for compatibility during migration
AttendanceRecord = AbsencePresence
Session = Seance

@login_required
def mark_attendance(request, token):
    if not request.user.is_student():
        messages.error(request, "Only students can mark attendance.")
        return redirect('dashboard')

    session = get_object_or_404(Session, token=token)
    
    # Check session expiration (30 minutes from start time)
    now = timezone.now()
    # Combine date and time (timezone aware)
    session_start = timezone.make_aware(timezone.datetime.combine(session.date, session.start_time))
    expiration_time = session_start + timezone.timedelta(minutes=30)
    
    if now > expiration_time:
        return render(request, 'attendance/error.html', {'message': "This QR code has expired (30 minute limit exceeded)."})

    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return render(request, 'attendance/error.html', {'message': "Your student profile is incomplete. Please contact the administrator to assign you to a class."})
    
    # Check if already marked
    if AttendanceRecord.objects.filter(student=student, session=session).exists():
        messages.info(request, "You have already marked attendance for this session.")
        return redirect('dashboard')

    # Create record
    AttendanceRecord.objects.create(
        student=student,
        session=session,
        status='present'
    )
    
    messages.success(request, f"Attendance marked for {session.classmodule.module.name}")
    return render(request, 'attendance/success.html', {'session': session})

@login_required
def student_history(request):
    if not request.user.is_student():
        return redirect('dashboard')
        
    try:
        student_obj = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Your student profile is incomplete. Please contact the administrator to assign you to a class.")
        return redirect('dashboard')
        
    # Get all past sessions for the student's class
    sessions = Session.objects.filter(
        classmodule__class_obj=student_obj.class_obj,
        date__lte=timezone.now().date()
    ).select_related('classmodule__module', 'classmodule__class_obj').order_by('-date', '-start_time')
    
    # Filter by module if specified
    module_filter = request.GET.get('module')
    if module_filter:
        sessions = sessions.filter(classmodule__module_id=module_filter)
    
    # Get all modules the student has attended for the filter dropdown
    from .models import Module, AbsenceJustification
    attended_modules = Module.objects.filter(
        classmodule__class_obj=student_obj.class_obj
    ).distinct().order_by('name')
    
    present_session_ids = set(AttendanceRecord.objects.filter(student=student_obj, status='present').values_list('session_id', flat=True))
    justifications = {j.session_id: j for j in AbsenceJustification.objects.filter(student=student_obj)}
    
    history_records = []
    for s in sessions:
        is_present = s.id in present_session_ids
        status = 'present' if is_present else 'absent'
        justification = justifications.get(s.id) if not is_present else None
        
        history_records.append({
            'session': s,
            'status': status,
            'timestamp': s.start_time,
            'justification': justification
        })
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(history_records, 15)  # 15 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    from .forms import JustificationForm
    form = JustificationForm()

    context = {
        'page_obj': page_obj,
        'attended_modules': attended_modules,
        'module_filter': module_filter,
        'justification_form': form
    }
    return render(request, 'attendance/student_history.html', context)

@login_required
def submit_justification(request, session_id):
    if not request.user.is_student() or request.method != 'POST':
        return redirect('dashboard')
        
    student_obj = get_object_or_404(Student, user=request.user)
    session = get_object_or_404(Seance, pk=session_id)
    
    from .forms import JustificationForm
    from .models import AbsenceJustification
    
    form = JustificationForm(request.POST, request.FILES)
    if form.is_valid():
        justification, created = AbsenceJustification.objects.get_or_create(
            student=student_obj,
            session=session,
            defaults={'document': form.cleaned_data['document']}
        )
        if not created: # If resubmitting, update document and reset to pending
            justification.document = form.cleaned_data['document']
            justification.status = 'pending'
            justification.save()
            
        messages.success(request, "Justification submitted successfully.")
    else:
        messages.error(request, "Failed to submit justification. Please upload a valid PDF.")
        
    return redirect('student_history')

@login_required
def scan_qr(request):
    if not request.user.is_student():
        messages.error(request, "Only students can scan QR codes.")
        return redirect('dashboard')
    return render(request, 'attendance/scan_qr.html')

from accounts.models import User

@login_required
def mark_manual_attendance(request, session_id):
    if not request.user.is_teacher() and not request.user.is_superuser:
        messages.error(request, "Only teachers can mark attendance manually.")
        return redirect('dashboard')
        
    session = get_object_or_404(Session, pk=session_id)
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        action = request.POST.get('action', 'present') # 'present' or 'absent'
        
        student_obj = get_object_or_404(Student, user__id=student_id)
        
        if action == 'present':
            AbsencePresence.objects.get_or_create(
                student=student_obj, 
                session=session, 
                defaults={'status': 'present'}
            )
            messages.success(request, f"Marked {student_obj.user.username} as present.")
        elif action == 'absent':
            AbsencePresence.objects.filter(student=student_obj, session=session).delete()
            messages.success(request, f"Marked {student_obj.user.username} as absent.")
            
    return redirect('session_detail', pk=session_id)
