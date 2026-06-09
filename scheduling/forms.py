from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.utils import timezone

from .models import HolidayClosure, RecoveryCredit, Section


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
