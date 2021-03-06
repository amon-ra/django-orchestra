from django.contrib import admin, messages
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from orchestra.admin.html import monospace_format
from orchestra.admin.utils import admin_link, admin_date, admin_colored

from . import settings, helpers
from .backends import ServiceBackend
from .models import Server, Route, BackendLog, BackendOperation
from .widgets import RouteBackendSelect


STATE_COLORS = {
    BackendLog.RECEIVED: 'darkorange',
    BackendLog.TIMEOUT: 'red',
    BackendLog.STARTED: 'blue',
    BackendLog.SUCCESS: 'green',
    BackendLog.FAILURE: 'red',
    BackendLog.ERROR: 'red',
    BackendLog.REVOKED: 'magenta',
}


class RouteAdmin(admin.ModelAdmin):
    list_display = (
        'backend', 'host', 'match', 'display_model', 'display_actions', 'is_active'
    )
    list_editable = ('host', 'match', 'is_active')
    list_filter = ('host', 'is_active', 'backend')
    ordering = ('backend',)
    
    BACKEND_HELP_TEXT = helpers.get_backends_help_text(ServiceBackend.get_backends())
    DEFAULT_MATCH = {
        backend.get_name(): backend.default_route_match for backend in ServiceBackend.get_backends()
    }
    
    def display_model(self, route):
        try:
            return escape(route.backend_class.model)
        except KeyError:
            return "<span style='color: red;'>NOT AVAILABLE</span>"
    display_model.short_description = _("model")
    display_model.allow_tags = True
    
    def display_actions(self, route):
        try:
            return '<br>'.join(route.backend_class.get_actions())
        except KeyError:
            return "<span style='color: red;'>NOT AVAILABLE</span>"
    display_actions.short_description = _("actions")
    display_actions.allow_tags = True
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        """ Provides dynamic help text on backend form field """
        if db_field.name == 'backend':
            kwargs['widget'] = RouteBackendSelect('this.id', self.BACKEND_HELP_TEXT, self.DEFAULT_MATCH)
        return super(RouteAdmin, self).formfield_for_dbfield(db_field, **kwargs)
    
    def get_form(self, request, obj=None, **kwargs):
        """ Include dynamic help text for existing objects """
        form = super(RouteAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            form.base_fields['backend'].help_text = self.BACKEND_HELP_TEXT.get(obj.backend, '')
        return form
    
    def show_orchestration_disabled(self, request):
        if settings.ORCHESTRATION_DISABLE_EXECUTION:
            msg = _("Orchestration execution is disabled by <tt>ORCHESTRATION_DISABLE_EXECUTION</tt> setting.")
            self.message_user(request, mark_safe(msg), messages.WARNING)
    
    def changelist_view(self, request, extra_context=None):
        self.show_orchestration_disabled(request)
        return super(RouteAdmin, self).changelist_view(request, extra_context)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        self.show_orchestration_disabled(request)
        return super(RouteAdmin, self).changeform_view(request, object_id, form_url, extra_context)


class BackendOperationInline(admin.TabularInline):
    model = BackendOperation
    fields = ('action', 'instance_link')
    readonly_fields = ('action', 'instance_link')
    extra = 0
    can_delete = False
    
    class Media:
        css = {
            'all': ('orchestra/css/hide-inline-id.css',)
        }
    
    def instance_link(self, operation):
        try:
            return admin_link('instance')(self, operation)
        except:
            return _("deleted {0} {1}").format(
                escape(operation.content_type), escape(operation.object_id)
            )
    instance_link.allow_tags = True
    instance_link.short_description = _("Instance")
    
    def has_add_permission(self, *args, **kwargs):
        return False
    
    def get_queryset(self, request):
        queryset = super(BackendOperationInline, self).get_queryset(request)
        return queryset.prefetch_related('instance')


def display_mono(field):
    def display(self, log):
        return monospace_format(escape(getattr(log, field)))
    display.short_description = _(field)
    return display


class BackendLogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'backend', 'server_link', 'display_state', 'exit_code',
        'display_created', 'execution_time',
    )
    list_display_links = ('id', 'backend')
    list_filter = ('state', 'backend')
    inlines = [BackendOperationInline]
    fields = [
        'backend', 'server_link', 'state', 'mono_script', 'mono_stdout',
        'mono_stderr', 'mono_traceback', 'exit_code', 'task_id', 'display_created',
        'execution_time'
    ]
    readonly_fields = fields
    
    server_link = admin_link('server')
    display_created = admin_date('created_at', short_description=_("Created"))
    display_state = admin_colored('state', colors=STATE_COLORS)
    mono_script = display_mono('script')
    mono_stdout = display_mono('stdout')
    mono_stderr = display_mono('stderr')
    mono_traceback = display_mono('traceback')
    
    def get_queryset(self, request):
        """ Order by structured name and imporve performance """
        qs = super(BackendLogAdmin, self).get_queryset(request)
        return qs.select_related('server').defer('script', 'stdout')
    
    def has_add_permission(self, *args, **kwargs):
        return False


class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'os')
    list_filter = ('os',)


admin.site.register(Server, ServerAdmin)
admin.site.register(BackendLog, BackendLogAdmin)
admin.site.register(Route, RouteAdmin)
