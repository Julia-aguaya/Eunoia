from django.contrib import admin
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .application.onboarding import (
    create_student_onboarding,
    reset_temporary_password,
    resolve_temporary_password,
)
from .application.recovery_credits import expire_overdue_recovery_credits as expire_overdue_recovery_credits_use_case
from .models import (
    AuditLog,
    Booking,
    BookingSource,
    BookingStatus,
    ClassSession,
    HolidayClosure,
    MonthlyAccessStatus,
    RecoveryCredit,
    RecoveryCreditSource,
    RecoveryCreditStatus,
    Section,
    User,
    WeeklyClassSlot,
)
from .use_cases import (
    activate_student_monthly_access,
    apply_holiday_closure,
    create_booking,
    grant_manual_recovery_credit,
    mark_booking_attended,
    mark_booking_no_show,
    suspend_student_monthly_access,
)
class UserCreationAdminForm(forms.ModelForm):
    temporary_password = forms.CharField(
        required=False,
        strip=False,
        help_text='Si lo dejas vacio se usa la contrasena temporal configurada para onboarding manual.',
    )

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name',
            'role',
            'primary_section',
            'phone',
            'notes',
            'must_change_password',
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions',
        )

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data['email'])
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            resolve_temporary_password(cleaned_data.get('temporary_password'))
        return cleaned_data

    def save(self, commit=True):
        if not commit:
            user = super().save(commit=False)
            user.set_initial_password(
                resolve_temporary_password(self.cleaned_data.get('temporary_password')),
                require_password_change=self.cleaned_data.get('must_change_password', True),
            )
            return user

        return create_student_onboarding(
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            role=self.cleaned_data['role'],
            primary_section=self.cleaned_data.get('primary_section'),
            phone=self.cleaned_data.get('phone', ''),
            notes=self.cleaned_data.get('notes', ''),
            temporary_password=self.cleaned_data.get('temporary_password'),
            must_change_password=self.cleaned_data.get('must_change_password', True),
            is_active=self.cleaned_data.get('is_active', True),
            is_staff=self.cleaned_data.get('is_staff', False),
            is_superuser=self.cleaned_data.get('is_superuser', False),
            groups=self.cleaned_data.get('groups') or (),
            user_permissions=self.cleaned_data.get('user_permissions') or (),
        )


class UserChangeAdminForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        help_text='Las contrasenas no se muestran. Para resetear onboarding manual, carga una nueva contrasena temporal.',
    )
    temporary_password = forms.CharField(
        required=False,
        strip=False,
        help_text='Opcional. Si la completas, se reemplaza la contrasena actual por una temporal y se fuerza cambio en primer ingreso.',
    )

    class Meta:
        model = User
        fields = '__all__'

    def clean_password(self):
        return self.initial['password']

    def clean(self):
        cleaned_data = super().clean()
        temporary_password = cleaned_data.get('temporary_password')
        if temporary_password:
            password_validation.validate_password(temporary_password)
            cleaned_data['must_change_password'] = True
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        temporary_password = self.cleaned_data.get('temporary_password')
        if temporary_password:
            user.set_temporary_password(temporary_password)
        if commit:
            user.save()
            self.save_m2m()
        return user


class BookingAdminForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk is None and cleaned_data.get('status') not in {None, BookingStatus.BOOKED}:
            raise forms.ValidationError('New bookings must be created as booked reservations.')
        return cleaned_data

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)

        if self.instance.pk:
            return super().save(commit=True)

        reservation = create_booking(
            session_id=self.cleaned_data['session'].pk,
            student=self.cleaned_data['student'],
            source=self.cleaned_data.get('source') or BookingSource.FIXED_SLOT,
            used_recovery_credit_id=(
                self.cleaned_data['used_recovery_credit'].pk
                if self.cleaned_data.get('used_recovery_credit') is not None
                else None
            ),
        )
        booking = reservation.booking
        booking.notes = self.cleaned_data.get('notes', '')
        if booking.notes:
            booking.save(update_fields=['notes', 'updated_at'])
        self.instance = booking
        return booking


class RecoveryCreditAdminForm(forms.ModelForm):
    class Meta:
        model = RecoveryCredit
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            for field_name in ('source', 'status', 'expires_at', 'used_at', 'granted_by'):
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk is None:
            cleaned_data['source'] = RecoveryCreditSource.MANUAL
            cleaned_data['status'] = RecoveryCreditStatus.AVAILABLE
        return cleaned_data

    def save(self, commit=True, granted_by=None):
        if not commit:
            return super().save(commit=False)

        if self.instance.pk:
            return super().save(commit=True)

        credit = grant_manual_recovery_credit(
            student=self.cleaned_data['student'],
            section=self.cleaned_data['section'],
            granted_by=granted_by,
            reference_date=self.cleaned_data.get('origin_session').date if self.cleaned_data.get('origin_session') else None,
            notes=self.cleaned_data.get('notes', ''),
        )
        if self.cleaned_data.get('origin_session'):
            credit.origin_session = self.cleaned_data['origin_session']
            credit.save(update_fields=['origin_session', 'updated_at'])
        self.instance = credit
        return credit


@admin.action(description='Activar acceso mensual por pago')
def activate_access_by_payment(modeladmin, request, queryset):
    updated = 0
    skipped = 0
    for access in queryset:
        change = activate_student_monthly_access(
            student=access.student,
            actor=request.user,
            month=access.month,
            record_audit=True,
        )
        if change.changed:
            updated += 1
        else:
            skipped += 1

    modeladmin.message_user(
        request,
        f'Se activaron {updated} accesos mensuales. Sin cambios: {skipped}.',
    )


@admin.action(description='Suspender acceso operativo mensual')
def suspend_operational_access(modeladmin, request, queryset):
    updated = 0
    skipped = 0
    for access in queryset:
        change = suspend_student_monthly_access(
            student=access.student,
            actor=request.user,
            month=access.month,
            record_audit=True,
        )
        if change.changed:
            updated += 1
        else:
            skipped += 1

    modeladmin.message_user(
        request,
        f'Se suspendieron {updated} accesos mensuales. Sin cambios: {skipped}.',
    )


@admin.action(description='Expirar recuperaciones vencidas')
def expire_overdue_recovery_credits(modeladmin, request, queryset):
    expiration = expire_overdue_recovery_credits_use_case(
        credits=queryset,
        actor=request.user,
        on_date=timezone.localdate(),
        record_audit=True,
    )
    modeladmin.message_user(
        request,
        f'Se marcaron {expiration.expired_count} recuperaciones como vencidas. Sin cambios: {expiration.skipped_count}.',
    )


@admin.action(description='Marcar reservas como asistidas')
def mark_bookings_as_attended(modeladmin, request, queryset):
    updated = 0
    skipped = 0
    for booking in queryset:
        try:
            mark_booking_attended(booking_id=booking.pk, when=timezone.now())
        except ValidationError:
            skipped += 1
        else:
            updated += 1
    modeladmin.message_user(
        request,
        f'Se marcaron {updated} reservas como asistidas. Omitidas: {skipped}.',
    )


@admin.action(description='Marcar reservas como no-show')
def mark_bookings_as_no_show(modeladmin, request, queryset):
    updated = 0
    skipped = 0
    for booking in queryset:
        try:
            mark_booking_no_show(booking_id=booking.pk, when=timezone.now())
        except ValidationError:
            skipped += 1
        else:
            updated += 1
    modeladmin.message_user(
        request,
        f'Se marcaron {updated} reservas como no-show. Omitidas: {skipped}.',
    )


@admin.action(description='Aplicar cierre de feriado y procesar recuperaciones')
def apply_holiday_closures(modeladmin, request, queryset):
    processed = 0
    updated_sessions = 0
    created_credits = 0
    existing_credits = 0
    for closure in queryset:
        application = apply_holiday_closure(
            closure_date=closure.date,
            reason=closure.reason,
            notes=closure.notes,
            actor=request.user,
            record_audit=True,
        )
        result = application.result
        processed += 1
        updated_sessions += result['updated_sessions']
        created_credits += result['created_credits']
        existing_credits += result['existing_credits']
    modeladmin.message_user(
        request,
        (
            f'Se aplicaron {processed} feriados. '
            f'Sesiones actualizadas: {updated_sessions}. '
            f'Recuperaciones nuevas: {created_credits}. '
            f'Recuperaciones ya existentes: {existing_credits}.'
        ),
    )


@admin.action(description='Resetear contrasena temporal configurada')
def reset_temporary_passwords(modeladmin, request, queryset):
    result = reset_temporary_password(users=queryset)
    modeladmin.message_user(
        request,
        (
            f'Se resetearon {result.updated_count} usuarias con la contrasena temporal configurada '
            'y cambio obligatorio en primer ingreso.'
        ),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationAdminForm
    form = UserChangeAdminForm
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'role', 'primary_section', 'must_change_password', 'is_staff')
    list_filter = ('role', 'primary_section', 'must_change_password', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'primary_section__name')
    list_select_related = ('primary_section',)
    autocomplete_fields = ('primary_section',)
    actions = (reset_temporary_passwords,)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'primary_section', 'phone', 'notes')}),
        ('Access', {'fields': ('role', 'must_change_password', 'temporary_password', 'temporary_password_set_at')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'role',
                    'primary_section',
                    'phone',
                    'notes',
                    'temporary_password',
                    'must_change_password',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                ),
            },
        ),
    )
    readonly_fields = ('last_login', 'created_at', 'updated_at', 'temporary_password_set_at')


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'default_capacity', 'is_active')
    list_filter = ('is_active', 'code')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(WeeklyClassSlot)
class WeeklyClassSlotAdmin(admin.ModelAdmin):
    list_display = ('section', 'weekday', 'start_time', 'end_time', 'resolved_capacity', 'active_range', 'is_active')
    list_filter = ('section', 'weekday', 'is_active')
    search_fields = ('section__name', 'section__code', 'notes')
    list_select_related = ('section',)
    ordering = ('weekday', 'start_time', 'section__name')

    @admin.display(description='Capacity')
    def resolved_capacity(self, obj):
        return obj.capacity or obj.section.default_capacity

    @admin.display(description='Range')
    def active_range(self, obj):
        start = obj.starts_on.isoformat() if obj.starts_on else 'open'
        end = obj.ends_on.isoformat() if obj.ends_on else 'open'
        return f'{start} -> {end}'


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ('section', 'date', 'start_time', 'end_time', 'capacity', 'status', 'slot', 'holiday_closure')
    list_filter = ('section', 'status', 'date', 'holiday_closure')
    search_fields = ('section__name', 'section__code', 'notes', 'slot__notes')
    autocomplete_fields = ('slot', 'holiday_closure')
    list_select_related = ('section', 'slot', 'holiday_closure')
    date_hierarchy = 'date'
    ordering = ('-date', 'start_time', 'section__name')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingAdminForm
    list_display = (
        'student',
        'session',
        'status',
        'source',
        'used_recovery_credit',
        'moved_from_booking',
        'moved_to_session',
        'moved_to_booking_reference',
        'cancellation_generates_recovery',
        'cancelled_at',
        'cancelled_by',
    )
    list_filter = ('status', 'source', 'cancellation_generates_recovery', 'session__section')
    search_fields = ('student__email', 'student__first_name', 'student__last_name')
    autocomplete_fields = ('session', 'student', 'used_recovery_credit', 'moved_from_booking', 'moved_to_session', 'cancelled_by')
    list_select_related = ('student', 'session', 'session__section', 'used_recovery_credit', 'moved_from_booking', 'moved_to_session')
    actions = (mark_bookings_as_attended, mark_bookings_as_no_show)

    def get_fields(self, request, obj=None):
        if obj is None:
            return ['session', 'student', 'source', 'used_recovery_credit', 'notes']
        return super().get_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ('status',)
        return (
            'status',
            'moved_from_booking',
            'moved_to_session',
            'cancelled_at',
            'cancelled_by',
            'cancellation_generates_recovery',
            'attendance_marked_at',
        )

    @admin.display(description='Moved to booking')
    def moved_to_booking_reference(self, obj):
        return getattr(obj, 'moved_to_booking', None)


@admin.register(RecoveryCredit)
class RecoveryCreditAdmin(admin.ModelAdmin):
    form = RecoveryCreditAdminForm
    list_display = ('student', 'section', 'source', 'status', 'expires_at', 'used_at', 'granted_by', 'overdue')
    list_filter = ('status', 'source', 'section')
    search_fields = ('student__email', 'student__first_name', 'student__last_name', 'section__name', 'notes')
    autocomplete_fields = ('student', 'section', 'origin_session', 'granted_by')
    list_select_related = ('student', 'section', 'origin_session', 'granted_by')
    actions = (expire_overdue_recovery_credits,)

    def get_fields(self, request, obj=None):
        if obj is None:
            return ['student', 'section', 'origin_session', 'notes']
        return super().get_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ('source', 'status', 'expires_at', 'used_at', 'granted_by')
        return ('source', 'status', 'expires_at', 'used_at', 'granted_by')

    def save_form(self, request, form, change):
        return form.save(granted_by=request.user)

    @admin.display(boolean=True, description='Overdue')
    def overdue(self, obj):
        return obj.is_overdue()


@admin.register(HolidayClosure)
class HolidayClosureAdmin(admin.ModelAdmin):
    list_display = ('date', 'reason', 'recovery_credits_processed', 'created_by')
    list_filter = ('recovery_credits_processed',)
    search_fields = ('reason', 'notes')
    autocomplete_fields = ('created_by',)
    ordering = ('-date',)
    readonly_fields = ('created_by', 'recovery_credits_processed', 'created_at', 'updated_at')
    actions = (apply_holiday_closures,)

    def save_model(self, request, obj, form, change):
        application = apply_holiday_closure(
            closure_date=obj.date,
            reason=obj.reason,
            notes=obj.notes,
            actor=request.user,
            record_audit=True,
        )
        closure = application.closure
        obj.pk = closure.pk
        obj.date = closure.date
        obj.reason = closure.reason
        obj.notes = closure.notes
        obj.created_by = closure.created_by
        obj.recovery_credits_processed = closure.recovery_credits_processed
        obj.created_at = closure.created_at
        obj.updated_at = closure.updated_at
        result = application.result
        self.message_user(
            request,
            (
                f'Feriado aplicado para {closure.date}: '
                f'{result["updated_sessions"]} sesiones actualizadas, '
                f'{result["created_credits"]} recuperaciones creadas, '
                f'{result["existing_credits"]} recuperaciones ya existentes.'
            ),
        )


@admin.register(MonthlyAccessStatus)
class MonthlyAccessStatusAdmin(admin.ModelAdmin):
    list_display = ('student', 'month', 'status', 'booking_enabled', 'activated_at', 'deactivated_at', 'activated_by')
    list_filter = ('status', 'booking_enabled', 'month')
    search_fields = ('student__email', 'student__first_name', 'student__last_name', 'notes')
    autocomplete_fields = ('student', 'activated_by')
    list_select_related = ('student', 'activated_by')
    date_hierarchy = 'month'
    actions = (activate_access_by_payment, suspend_operational_access)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'entity_type', 'entity_id', 'actor', 'description')
    list_filter = ('action', 'entity_type')
    search_fields = ('description', 'entity_type', 'actor__email')
    autocomplete_fields = ('actor',)
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('actor',)
