from django.db import models
from django.conf import settings

class Class(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Module(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Teacher(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"Teacher: {self.user.username}"

class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE)

    def __str__(self):
        return f"Student: {self.user.username}"

class ClassModule(models.Model):
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.class_obj.name} - {self.module.name}"

class Seance(models.Model):
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    classmodule = models.ForeignKey(ClassModule, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.classmodule} on {self.date}"

class AbsencePresence(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    session = models.ForeignKey(Seance, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, null=True, blank=True) # Made nullable to be safe

    class Meta:
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.student.user.username} - {self.session.date}: {self.status}"

class AbsenceJustification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    session = models.ForeignKey(Seance, on_delete=models.CASCADE)
    document = models.FileField(upload_to='justifications/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Justification for {self.student.user.username} - {self.session.date} ({self.status})"

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_teacher_profile(sender, instance, created, **kwargs):
    if instance.role == 'teacher':
        Teacher.objects.get_or_create(user=instance)
