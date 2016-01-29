from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm

from .models import MyUser

class PermissionAdmin(admin.ModelAdmin):
    search_fields = ['name', 'codename']

class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'confirmed']
    fieldsets = (
        (None, {'fields': ('email', 'password',)}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'date_joined', 'last_login',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)}),
    )
    add_fieldsets = (
        (None, {'fields':
                ('email', 'first_name', 'last_name', 'password1', 'password2'),
                }),)
    search_fields = ('email', 'first_name', 'last_name',)
    ordering = ('last_name', 'first_name',)
    actions = ['send_email_invitation']

    # TODO - include alternative messages for warning/failure
    def send_email_invitation(self, request, queryset):
        for user in queryset:
            reset_form = PasswordResetForm({'email': user.email}, request.POST)
            assert reset_form.is_valid()
            reset_form.save(
                subject_template_name='common_auth/emails/account_creation_subject.txt',
                email_template_name='common_auth/emails/invitation_email.html',
                request=request
            )

        self.message_user(request, 'Email invitation successfully sent')
    send_email_invitation.short_description = 'Send email invitation to selected users'

admin.site.register(MyUser, CustomUserAdmin)
admin.site.register(Permission, PermissionAdmin)
