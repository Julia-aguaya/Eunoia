from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.utils import timezone

from .models import (
    ClassSession,
    HolidayClosure,
    RecoveryCredit,
    Section,
    SessionStatus,
    StudentMonthlyPlan,
    WeeklyClassSlot,
    merge_notes_with_legacy_userselections_metadata,
    normalize_month_start,
    strip_legacy_userselections_notes,
)


class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'autocomplete': 'username',
                'autofocus': True,
                'placeholder': 'nombre@dominio.com',
            }
        )
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'placeholder': 'Tu contrasena',
            }
        ),
    )

    error_messages = {
        'invalid_login': 'No pudimos iniciar sesion con esos datos. Revisa email y contrasena.',
        'inactive': 'Esta cuenta esta inactiva. Contacta al staff para reactivarla.',
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user_cache = None

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                inactive_user = get_user_model().objects.filter(email__iexact=email, is_active=False).first()
                if inactive_user is not None and inactive_user.check_password(password):
                    raise forms.ValidationError(self.error_messages['inactive'])
                raise forms.ValidationError(self.error_messages['invalid_login'])
            if not self.user_cache.is_active:
                raise forms.ValidationError(self.error_messages['inactive'])

        return cleaned_data

    def get_user(self):
        return self.user_cache


class StudentSelfSignupForm(forms.Form):
    first_name = forms.CharField(label='Nombre', max_length=100)
    last_name = forms.CharField(label='Apellido', max_length=100)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='Teléfono', max_length=50, required=False)
    primary_section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        label='Actividad',
        empty_label=None,
    )
    password1 = forms.CharField(label='Contraseña', strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label='Repetir contraseña', strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['primary_section'].queryset = Section.objects.filter(is_active=True).order_by('name')
        self.fields['email'].widget.attrs.update({'autocomplete': 'email', 'autocapitalize': 'none', 'spellcheck': 'false'})
        self.fields['phone'].widget.attrs.update({'autocomplete': 'tel'})
        self.fields['password1'].widget.attrs.update({'autocomplete': 'new-password'})
        self.fields['password2'].widget.attrs.update({'autocomplete': 'new-password'})

    def clean_email(self):
        email = get_user_model().objects.normalize_email(self.cleaned_data['email'])
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese email.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')

        if password1:
            password_validation.validate_password(password1)

        return cleaned_data


class RequiredPasswordChangeForm(forms.Form):
    new_password1 = forms.CharField(
        label='Nueva contrasena',
        strip=False,
        widget=forms.PasswordInput,
    )
    new_password2 = forms.CharField(
        label='Repetir nueva contrasena',
        strip=False,
        widget=forms.PasswordInput,
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Las contrasenas nuevas no coinciden.')

        if password1:
            password_validation.validate_password(password1, self.user)

        return cleaned_data

    def save(self):
        self.user.set_initial_password(self.cleaned_data['new_password1'], require_password_change=False)
        self.user.save(update_fields=['password', 'must_change_password', 'temporary_password_set_at', 'updated_at'])
        return self.user


class AccountProfileForm(forms.ModelForm):
    current_password = forms.CharField(
        required=False,
        label='Contrasena actual',
        strip=False,
        widget=forms.PasswordInput,
    )
    new_password1 = forms.CharField(
        required=False,
        label='Nueva contrasena',
        strip=False,
        widget=forms.PasswordInput,
    )
    new_password2 = forms.CharField(
        required=False,
        label='Repetir nueva contrasena',
        strip=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'phone']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Email',
            'phone': 'Telefono',
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, instance=user, **kwargs)
        self.user = user
        self.fields['email'].widget.attrs.update({'autocomplete': 'email'})
        self.fields['phone'].widget.attrs.update({'autocomplete': 'tel'})

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese email.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        wants_password_change = bool(current_password or new_password1 or new_password2)

        if not wants_password_change:
            return cleaned_data

        if not current_password:
            self.add_error('current_password', 'Ingresa tu contrasena actual para cambiarla.')
        elif not self.user.check_password(current_password):
            self.add_error('current_password', 'La contrasena actual no coincide.')

        if not new_password1:
            self.add_error('new_password1', 'Ingresa una nueva contrasena.')

        if not new_password2:
            self.add_error('new_password2', 'Repeti la nueva contrasena.')

        if new_password1 and new_password2 and new_password1 != new_password2:
            self.add_error('new_password2', 'Las contrasenas nuevas no coinciden.')

        if new_password1:
            password_validation.validate_password(new_password1, self.user)

        return cleaned_data

    def save(self):
        user = super().save(commit=False)
        new_password1 = self.cleaned_data.get('new_password1')
        if new_password1:
            user.set_initial_password(new_password1, require_password_change=False)
        user.save()
        return user


class StaffManualRecoveryCreditForm(forms.Form):
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        label='Actividad de la recuperacion',
        empty_label=None,
    )
    notes = forms.CharField(
        required=False,
        label='Motivo breve',
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Opcional. Sirve para dejar una referencia operativa corta.',
    )

    def __init__(self, *, student, **kwargs):
        super().__init__(**kwargs)
        self.student = student
        self.fields['section'].queryset = Section.objects.filter(is_active=True).order_by('name')
        if student.primary_section_id:
            self.fields['section'].initial = student.primary_section_id
            self.fields['section'].help_text = 'Sale preseleccionada la actividad principal de la alumna.'

    def save(self, *, granted_by):
        return RecoveryCredit.objects.grant_manual_credit(
            student=self.student,
            section=self.cleaned_data['section'],
            granted_by=granted_by,
            reference_date=timezone.localdate(),
            notes=self.cleaned_data.get('notes', '').strip(),
        )


class StaffStudentMonthlyPlanForm(forms.Form):
    month = forms.DateField(
        required=True,
        label='Mes',
        input_formats=['%Y-%m', '%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m', attrs={'type': 'month'}),
    )
    monthly_plan_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        label='Actividad',
    )
    slot_ids = forms.ModelMultipleChoiceField(
        queryset=WeeklyClassSlot.objects.none(),
        label='Horarios fijos del mes',
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    notes = forms.CharField(
        required=False,
        label='Notas operativas',
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': 'Ej: priorizar este combo si pide mover una clase o si hay un criterio operativo a recordar.',
            }
        ),
    )

    def __init__(self, *, student, month, section=None, **kwargs):
        super().__init__(**kwargs)
        self.student = student
        self.month = normalize_month_start(month)
        self.selected_section = None
        self.fields['month'].initial = self.month
        available_sections = Section.objects.filter(is_active=True).order_by('name')
        self.fields['section'].queryset = available_sections

        effective_plans = student.get_effective_monthly_plans_for(self.month)
        default_section = section or (effective_plans[0].section if effective_plans else student.primary_section)
        if default_section is not None:
            self.fields['section'].initial = default_section.pk

        if self.is_bound:
            raw_section_id = self.data.get(self.add_prefix('section'))
            self.selected_section = available_sections.filter(pk=raw_section_id).first()
        elif default_section is not None:
            self.selected_section = available_sections.filter(pk=default_section.pk).first() or default_section

        self.plan = None
        self.effective_plan = None
        if self.selected_section is not None:
            self.plan = student.get_monthly_plan_for_section(self.month, section=self.selected_section)
            self.effective_plan = self.plan or student.get_effective_monthly_plan_for_section(self.month, section=self.selected_section)

        queryset = WeeklyClassSlot.objects.none()
        help_text = 'Elegí una actividad para ver y guardar los horarios del plan mensual.'
        if self.selected_section is not None:
            queryset = WeeklyClassSlot.objects.filter(section=self.selected_section, is_active=True).order_by('weekday', 'start_time')
            help_text = 'Elegí uno o mas horarios semanales de la actividad seleccionada para armar el plan del mes.'
        self.fields['slot_ids'].queryset = queryset
        self.fields['slot_ids'].help_text = help_text
        self.fields['notes'].help_text = 'Opcional. Dejá contexto corto para el equipo si este plan necesita seguimiento.'
        self.fields['notes'].widget.attrs['class'] = 'wizard-notes'

        initial_plan = self.effective_plan
        if initial_plan is not None and not self.is_bound:
            if self.plan is not None:
                self.initial['monthly_plan_id'] = self.plan.pk
            if self.selected_section is not None:
                self.initial['section'] = self.selected_section.pk
            else:
                self.initial['section'] = initial_plan.section_id
            self.initial['notes'] = strip_legacy_userselections_notes(initial_plan.notes)
            if self.selected_section is not None and initial_plan.section_id == self.selected_section.pk:
                self.initial['slot_ids'] = list(initial_plan.plan_slots.values_list('weekly_class_slot_id', flat=True).order_by('position'))

    def clean_month(self):
        return normalize_month_start(self.cleaned_data['month'])

    def clean_slot_ids(self):
        return list(self.cleaned_data.get('slot_ids') or [])

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        selected_section = cleaned_data.get('section')
        if selected_section is None:
            raise forms.ValidationError('Elegí una actividad para configurar el plan mensual.')

        for slot in cleaned_data.get('slot_ids', []):
            if slot.section_id != selected_section.id:
                raise forms.ValidationError('Todos los horarios del plan mensual tienen que pertenecer a la actividad seleccionada.')

        return cleaned_data

    def save(self):
        plan = self.plan or StudentMonthlyPlan(
            student=self.student,
            month=self.cleaned_data['month'],
            section=self.cleaned_data['section'],
        )
        plan.month = self.cleaned_data['month']
        plan.section = self.cleaned_data['section']
        plan.notes = merge_notes_with_legacy_userselections_metadata(
            self.cleaned_data.get('notes', '').strip(),
            existing_notes=plan.notes,
        )
        plan.replace_weekly_slots(self.cleaned_data['slot_ids'])
        return plan


class StaffHolidayClosureForm(forms.ModelForm):
    class Meta:
        model = HolidayClosure
        fields = ['date', 'reason', 'notes']
        labels = {
            'date': 'Dia a cerrar',
            'reason': 'Motivo visible',
            'notes': 'Notas operativas',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'reason': 'Ej: feriado nacional, mantenimiento edilicio o cierre excepcional.',
            'notes': 'Opcional. Sirve para dejar contexto interno corto.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = self.initial.get('date') or timezone.localdate()

    def validate_unique(self):
        return


class StaffClassSessionForm(forms.Form):
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        label='Actividad',
        empty_label=None,
    )
    date = forms.DateField(
        label='Día',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    start_time = forms.TimeField(
        label='Hora de inicio',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    end_time = forms.TimeField(
        label='Hora de fin',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    capacity = forms.IntegerField(
        label='Cupo',
        min_value=1,
    )

    def __init__(self, *args, session_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_instance = session_instance
        self.fields['section'].queryset = Section.objects.filter(is_active=True).order_by('name')
        if session_instance is not None:
            self.fields['section'].initial = session_instance.section_id
            self.fields['date'].initial = session_instance.date
            self.fields['start_time'].initial = session_instance.start_time
            self.fields['end_time'].initial = session_instance.end_time
            self.fields['capacity'].initial = session_instance.capacity
        else:
            self.fields['date'].initial = self.initial.get('date') or timezone.localdate()

    def clean(self):
        cleaned_data = super().clean()
        section = cleaned_data.get('section')
        session_date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', 'La hora de fin tiene que ser posterior al inicio.')

        if section and session_date and start_time:
            duplicate_qs = ClassSession.objects.filter(
                section=section,
                date=session_date,
                start_time=start_time,
            )
            if self.session_instance is not None:
                duplicate_qs = duplicate_qs.exclude(pk=self.session_instance.pk)
            if duplicate_qs.exists():
                self.add_error('start_time', 'Ya existe una clase para esa actividad en ese día y horario.')

        return cleaned_data

    def save(self):
        if self.session_instance is None:
            return ClassSession.objects.create(
                section=self.cleaned_data['section'],
                date=self.cleaned_data['date'],
                start_time=self.cleaned_data['start_time'],
                end_time=self.cleaned_data['end_time'],
                capacity=self.cleaned_data['capacity'],
                status=SessionStatus.SCHEDULED,
            )

        session = self.session_instance
        session.section = self.cleaned_data['section']
        session.date = self.cleaned_data['date']
        session.start_time = self.cleaned_data['start_time']
        session.end_time = self.cleaned_data['end_time']
        session.capacity = self.cleaned_data['capacity']
        session.save(update_fields=['section', 'date', 'start_time', 'end_time', 'capacity', 'updated_at'])
        return session
