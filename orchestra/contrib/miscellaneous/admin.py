from django import forms
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from orchestra.admin import ExtendedModelAdmin
from orchestra.admin.utils import admin_link
from orchestra.contrib.accounts.admin import AccountAdminMixin
from orchestra.plugins import PluginModelAdapter
from orchestra.plugins.admin import SelectPluginAdminMixin
from orchestra.utils.python import import_class

from . import settings
from .models import MiscService, Miscellaneous


class MiscServicePlugin(PluginModelAdapter):
    model = MiscService
    name_field = 'name'


class MiscServiceAdmin(ExtendedModelAdmin):
    list_display = (
        'name', 'verbose_name', 'num_instances', 'has_identifier', 'has_amount', 'is_active'
    )
    list_editable = ('is_active',)
    list_filter = ('has_identifier', 'has_amount', 'is_active')
    fields = (
        'verbose_name', 'name', 'description', 'has_identifier', 'has_amount', 'is_active'
    )
    prepopulated_fields = {'name': ('verbose_name',)}
    change_readonly_fields = ('name',)
    
    def num_instances(self, misc):
        """ return num slivers as a link to slivers changelist view """
        num = misc.instances__count
        url = reverse('admin:miscellaneous_miscellaneous_changelist')
        url += '?service={}'.format(misc.pk)
        return mark_safe('<a href="{0}">{1}</a>'.format(url, num))
    num_instances.short_description = _("Instances")
    num_instances.admin_order_field = 'instances__count'
    
    def get_queryset(self, request):
        qs = super(MiscServiceAdmin, self).get_queryset(request)
        return qs.annotate(models.Count('instances', distinct=True))
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        """ Make value input widget bigger """
        if db_field.name == 'description':
            kwargs['widget'] = forms.Textarea(attrs={'cols': 70, 'rows': 2})
        return super(MiscServiceAdmin, self).formfield_for_dbfield(db_field, **kwargs)


class MiscellaneousAdmin(AccountAdminMixin, SelectPluginAdminMixin, admin.ModelAdmin):
    list_display = (
        '__str__', 'service_link', 'amount', 'dispaly_active', 'account_link', 'is_active'
    )
    list_filter = ('service__name', 'is_active')
    list_select_related = ('service', 'account')
    search_fields = ('identifier', 'description', 'account__username')
    plugin_field = 'service'
    plugin = MiscServicePlugin
    
    service_link = admin_link('service')
    
    def dispaly_active(self, instance):
        return instance.active
    dispaly_active.short_description = _("Active")
    dispaly_active.boolean = True
    dispaly_active.admin_order_field = 'is_active'
    
    def get_service(self, obj):
        if obj is None:
            return self.plugin.get(self.plugin_value).related_instance
        else:
            return obj.service
    
    def get_fields(self, request, obj=None):
        fields = ['account', 'description', 'is_active']
        if obj is not None:
            fields = ['account_link', 'description', 'is_active']
        service = self.get_service(obj)
        if service.has_amount:
            fields.insert(-1, 'amount')
        if service.has_identifier:
            fields.insert(1, 'identifier')
        return fields
    
    def get_form(self, request, obj=None, **kwargs):
        form = super(SelectPluginAdminMixin, self).get_form(request, obj, **kwargs)
        service = self.get_service(obj)
        def clean_identifier(self, service=service):
            identifier = self.cleaned_data['identifier']
            validator_path = settings.MISCELLANEOUS_IDENTIFIER_VALIDATORS.get(service.name, None)
            validator = import_class(validator_path)
            if validator:
                validator(identifier)
            return identifier
        
        form.clean_identifier = clean_identifier
        return form
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        """ Make value input widget bigger """
        if db_field.name == 'description':
            kwargs['widget'] = forms.Textarea(attrs={'cols': 70, 'rows': 4})
        return super(MiscellaneousAdmin, self).formfield_for_dbfield(db_field, **kwargs)
    
    def save_model(self, request, obj, form, change):
        if not change:
            plugin = self.plugin
            kwargs = {
                plugin.name_field: self.plugin_value
            }
            setattr(obj, self.plugin_field, plugin.model.objects.get(**kwargs))
        obj.save()

admin.site.register(MiscService, MiscServiceAdmin)
admin.site.register(Miscellaneous, MiscellaneousAdmin)
