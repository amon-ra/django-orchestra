import re
import textwrap

from django.utils.translation import ugettext_lazy as _

from orchestra.contrib.orchestration import ServiceController, replace
from orchestra.contrib.orchestration import Operation
from orchestra.utils.python import OrderedSet

from . import settings


class Bind9MasterDomainBackend(ServiceController):
    """
    Bind9 zone and config generation.
    It auto-discovers slave Bind9 servers based on your routing configuration or you can use DOMAINS_SLAVES to explicitly configure the slaves.
    """
    CONF_PATH = settings.DOMAINS_MASTERS_PATH
    
    verbose_name = _("Bind9 master domain")
    model = 'domains.Domain'
    related_models = (
        ('domains.Record', 'domain__origin'),
        ('domains.Domain', 'origin'),
    )
    ignore_fields = ['serial']
    doc_settings = (settings,
        ('DOMAINS_SLAVES', 'DOMAINS_MASTERS_PATH')
    )
    
    @classmethod
    def is_main(cls, obj):
        """ work around Domain.top self relationship """
        if super(Bind9MasterDomainBackend, cls).is_main(obj):
            return not obj.top
    
    def save(self, domain):
        context = self.get_context(domain)
        domain.refresh_serial()
        self.update_zone(domain, context)
        self.update_conf(context)
    
    def update_zone(self, domain, context):
        context['zone'] = ';; %(banner)s\n' % context
        context['zone'] += domain.render_zone().replace("'", '"')
        self.append(textwrap.dedent("""\
            echo -e '%(zone)s' > %(zone_path)s.tmp
            diff -N -I'^\s*;;' %(zone_path)s %(zone_path)s.tmp || UPDATED=1
            # Because bind reload will not display any fucking error
            named-checkzone -k fail -n fail %(name)s %(zone_path)s.tmp
            mv %(zone_path)s.tmp %(zone_path)s
            """) % context
        )
    
    def update_conf(self, context):
        self.append(textwrap.dedent("""\
            conf='%(conf)s'
            sed '/zone "%(name)s".*/,/^\s*};\s*$/!d' %(conf_path)s | diff -B -I"^\s*//" - <(echo "${conf}") || {
                sed -i -e '/zone\s\s*"%(name)s".*/,/^\s*};/d' \\
                       -e 'N; /^\s*\\n\s*$/d; P; D' %(conf_path)s
                echo "${conf}" >> %(conf_path)s
                UPDATED=1
            }""") % context
        )
        # Delete ex-top-domains that are now subdomains
        self.append(textwrap.dedent("""\
            sed -i -e '/zone\s\s*".*\.%(name)s".*/,/^\s*};\s*$/d' \\
                   -e 'N; /^\s*\\n\s*$/d; P; D' %(conf_path)s""") % context
        )
        if 'zone_path' in context:
            context['zone_subdomains_path'] = re.sub(r'^(.*/)', r'\1*.', context['zone_path'])
            self.append('rm -f %(zone_subdomains_path)s' % context)
    
    def delete(self, domain):
        context = self.get_context(domain)
        self.append('rm -f %(zone_path)s;' % context)
        self.delete_conf(context)
    
    def delete_conf(self, context):
        if context['name'][0] in ('*', '_'):
            # These can never be top level domains
            return
        self.append(textwrap.dedent("""\
            sed -e '/zone\s\s*"%(name)s".*/,/^\s*};\s*$/d' \\
                -e 'N; /^\s*\\n\s*$/d; P; D' %(conf_path)s > %(conf_path)s.tmp""") % context
        )
        self.append('diff -B -I"^\s*//" %(conf_path)s.tmp %(conf_path)s || UPDATED=1' % context)
        self.append('mv %(conf_path)s.tmp %(conf_path)s' % context)
    
    def commit(self):
        """ reload bind if needed """
        self.append('if [[ $UPDATED == 1 ]]; then service bind9 reload; fi')
    
    def get_servers(self, domain, backend):
        """ Get related server IPs from registered backend routes """
        from orchestra.contrib.orchestration.manager import router
        operation = Operation(backend, domain, Operation.SAVE)
        servers = []
        for server in router.get_servers(operation):
            servers.append(server.get_ip())
        return servers
    
    def get_slaves(self, domain):
        ips = list(settings.DOMAINS_SLAVES)
        ips += self.get_servers(domain, Bind9SlaveDomainBackend)
        return OrderedSet(ips)
    
    def get_context(self, domain):
        slaves = self.get_slaves(domain)
        context = {
            'name': domain.name,
            'zone_path': settings.DOMAINS_ZONE_PATH % {'name': domain.name},
            'subdomains': domain.subdomains.all(),
            'banner': self.get_banner(),
            'slaves': '; '.join(slaves) or 'none',
            'also_notify': '; '.join(slaves) + ';' if slaves else '',
            'conf_path': self.CONF_PATH,
        }
        context['conf'] = textwrap.dedent("""
            zone "%(name)s" {
                // %(banner)s
                type master;
                file "%(zone_path)s";
                allow-transfer { %(slaves)s; };
                also-notify { %(also_notify)s };
                notify yes;
            };""") % context
        return replace(context, "'", '"')


class Bind9SlaveDomainBackend(Bind9MasterDomainBackend):
    """
    Generate the configuartion for slave servers
    It auto-discover the master server based on your routing configuration or you can use DOMAINS_MASTERS to explicitly configure the master.
    """
    CONF_PATH = settings.DOMAINS_SLAVES_PATH
    
    verbose_name = _("Bind9 slave domain")
    related_models = (
        ('domains.Domain', 'origin'),
    )
    doc_settings = (settings,
        ('DOMAINS_MASTERS', 'DOMAINS_SLAVES_PATH')
    )
    def save(self, domain):
        context = self.get_context(domain)
        self.update_conf(context)
    
    def delete(self, domain):
        context = self.get_context(domain)
        self.delete_conf(context)
    
    def commit(self):
        """ ideally slave should be restarted after master """
        self.append('if [[ $UPDATED == 1 ]]; then { sleep 1 && service bind9 reload; } & fi')
    
    def get_masters(self, domain):
        ips = list(settings.DOMAINS_MASTERS)
        ips += self.get_servers(domain, Bind9MasterDomainBackend)
        return OrderedSet(ips)
    
    def get_context(self, domain):
        context = {
            'name': domain.name,
            'banner': self.get_banner(),
            'subdomains': domain.subdomains.all(),
            'masters': '; '.join(self.get_masters(domain)) or 'none',
            'conf_path': self.CONF_PATH,
        }
        context['conf'] = textwrap.dedent("""
            zone "%(name)s" {
                // %(banner)s
                type slave;
                file "%(name)s";
                masters { %(masters)s; };
                allow-notify { %(masters)s; };
            };""") % context
        return replace(context, "'", '"')
