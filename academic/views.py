from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from attendance.models import Seance, ClassModule, Teacher, Student
from .forms import SessionForm
import qrcode
from django.http import HttpResponse
from io import BytesIO
from django.core.paginator import Paginator
import uuid

@login_required
def create_session(request):
    if not request.user.role == 'teacher':
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = SessionForm(request.POST, user=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            if not session.token:
                session.token = str(uuid.uuid4())
            session.save()
            return redirect('session_detail', pk=session.pk)
    else:
        form = SessionForm(user=request.user)
    return render(request, 'academic/create_session.html', {'form': form})

@login_required
def session_list(request):
    sessions = Seance.objects.all()
    if request.user.role == 'teacher':
        try:
            teacher_obj = Teacher.objects.get(user=request.user)
            sessions = sessions.filter(classmodule__teacher=teacher_obj)
        except Teacher.DoesNotExist:
            sessions = Seance.objects.none()
    
    # Filter by date
    date_filter = request.GET.get('date')
    if date_filter:
        sessions = sessions.filter(date=date_filter)
        
    # Filter by classmodule (from dashboard links)
    cm_id = request.GET.get('classmodule_id')
    if cm_id:
        sessions = sessions.filter(classmodule_id=cm_id)
        
    sessions = sessions.order_by('-date', '-start_time')
    
    # Pagination
    paginator = Paginator(sessions, 5) # 10 sessions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'academic/session_list.html', {'page_obj': page_obj, 'date_filter': date_filter})

@login_required
def session_detail(request, pk):
    session = get_object_or_404(Seance, pk=pk)
    
    # Get all students in this class
    class_students = Student.objects.filter(class_obj=session.classmodule.class_obj).select_related('user')
    
    # Get IDs of students already marked present for this session
    present_student_ids = session.absencepresence_set.filter(status='present').values_list('student_id', flat=True)
    
    # Attach attendance status to each student object for the template
    for student in class_students:
        student.is_present = student.id in present_student_ids

    context = {
        'session': session,
        'students': class_students,
        'present_count': len(present_student_ids),
        'total_count': class_students.count()
    }
    return render(request, 'academic/session_detail.html', context)

@login_required
def generate_qr(request, session_id):
    session = get_object_or_404(Seance, pk=session_id)
    # URL that student scans
    attendance_url = request.build_absolute_uri(f'/attendance/mark/{session.token}/')
    
    img = qrcode.make(attendance_url)
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='image/png')

@login_required
def session_attendance_list(request, session_id):
    session = get_object_or_404(Seance, pk=session_id)
    # Ensure only the teacher of the course can view this (or admin)
    try:
        teacher_obj = Teacher.objects.get(user=request.user)
        if session.classmodule.teacher != teacher_obj and not request.user.is_admin():
             return redirect('dashboard')
    except Teacher.DoesNotExist:
        if not request.user.is_admin():
            return redirect('dashboard')

    attendances = session.absencepresence_set.select_related('student__user').all()
    return render(request, 'academic/session_attendance_list.html', {'session': session, 'attendances': attendances})

from attendance.models import AbsenceJustification
from django.contrib import messages

@login_required
def teacher_justifications(request):
    if request.user.role != 'teacher':
        return redirect('dashboard')
        
    try:
        teacher_obj = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return redirect('dashboard')
        
    # Get all justifications for sessions taught by this teacher
    justifications = AbsenceJustification.objects.filter(
        session__classmodule__teacher=teacher_obj
    ).select_related('student__user', 'session__classmodule__module', 'session__classmodule__class_obj').order_by('-submitted_at')
    
    # Pagination
    paginator = Paginator(justifications, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'academic/justifications_list.html', {'page_obj': page_obj})

@login_required
def review_justification(request, justification_id):
    if request.user.role != 'teacher':
        return redirect('dashboard')
        
    justification = get_object_or_404(AbsenceJustification, pk=justification_id)
    
    # Verify the teacher owns this session
    try:
        teacher_obj = Teacher.objects.get(user=request.user)
        if justification.session.classmodule.teacher != teacher_obj:
            return redirect('teacher_justifications')
    except Teacher.DoesNotExist:
        return redirect('dashboard')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ['approved', 'declined']:
            justification.status = action
            justification.save()
            messages.success(request, f"Justification {action} successfully.")
            
    return redirect('teacher_justifications')