from common.signals import collect_related_objects_to_delete
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
import re
import settings

class Zone(models.Model):
    origin = models.CharField(max_length=255)
    primary_ns = models.CharField(max_length=255, default=settings.DEFAULT_PRIMARY_NS)
    hostmaster_email = models.CharField(max_length=255, default=settings.DEFAULT_HOSTMASTER_EMAIL)

    expire = models.DateField(null=True, blank=True)
    serial = models.IntegerField(default=settings.DOMAIN_SERIAL)
    slave_refresh = models.CharField(default=settings.DOMAIN_SLAVE_REFRESH, max_length=16)
    slave_retry = models.CharField(default=settings.DOMAIN_SLAVE_RETRY, max_length=8)
    slave_expiration = models.CharField(default=settings.DOMAIN_SLAVE_EXPIRATION, max_length=8)
    min_caching_time = models.CharField(default=settings.DOMAIN_MIN_CACHING_TIME, max_length=8)

    # TODO: create a virtual relation with name in order to deprecate the signal approach of auto deletions.

    def __unicode__(self):
        return str(self.origin)

    def get_names(self):
        names = [self.origin]
        for record in self.record_set.filter(Q(Q(type='CNAME') | Q(type='A')) & Q(name__gt='')):
            names.append("%s.%s" % (record.name, self.origin))
        return names


class Record(models.Model):
    """ Domain Record """
    zone = models.ForeignKey(Zone)
    name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=6, choices=settings.REGISTER_CHOICES)
    data = models.CharField(max_length=128)
    
    def __unicode__(self):
        return "%s.%s-%s.%s" % (self.zone, self.name, self.type, self.data)


class Name(models.Model):
    """ Track and manage the registration of domain names. 
        This model is also useful for other models that needs domains: i.e. web.VirtualHost """
    name = models.CharField(max_length=255)
    extension = models.CharField(max_length=8, choices=settings.EXTENSIONS, default=settings.DEFAULT_EXTENSION)
    register_provider = models.CharField(max_length=255, blank=True,
        choices=settings.REGISTER_PROVIDER_CHOICES, default=settings.DEFAULT_REGISTER_PROVIDER)
    # TODO: this contact FK approach is bullshit (dependencies are bad :()
    administrative_contact = models.ForeignKey('contacts.BaseContact', related_name='administrative_contact_name_set', null=True, blank=True)
    technical_contact = models.ForeignKey('contacts.BaseContact', related_name='technical_contact_name_set', null=True, blank=True) 
    billing_contact = models.ForeignKey('contacts.BaseContact', related_name='billing_contact_name_set', null=True, blank=True)

    # TODO: create a virtual relation with zone in order to deprecate the signal approach of auto deletions.

    class Meta:
        unique_together = ('name', 'extension')
    
    def __unicode__(self):
        return "%s.%s" % (self.name, self.extension)

    def save(self, *args, **kwargs):
        if self.pk:
            old = Name.objects.get(pk=self.pk)
            if old.name != self.name or old.extension != self.extension:
                #TODO: raise form error
                raise AttributeError('Change name or extension are not allowed')
        super(Name, self).save(*args, **kwargs)

    def get_zone(self):
        """ return a related Zone if exists, else return None """
    
        entair_origin = "%s.%s" % (self.name, self.extension)
        position = entair_origin.rindex('.')
        stop = False
        
        while not stop:
            try: position = entair_origin.rindex('.', 0, position)
            except ValueError: 
                origin = entair_origin
                record = ''
                stop = True
            else:
                origin = entair_origin[position+1:]
                record = entair_origin[:position]
            
            zone = Zone.objects.filter(origin=origin, record__name=record).distinct()
            if len(zone) > 0: return zone[0]     
        
        return None

    def get_record(self):
        zone = self.get_zone()
        domain_name = "%s.%s" % (self.name, self.extension)
        record_name = re.sub("\.%s$" % zone.origin.replace('.', '\.'), '', domain_name)
        return Record.objects.get(name=record_name, zone=zone)

    @classmethod
    def get_extension(cls, domain):
        s_cmp = lambda n, k: k[0].count('.') - n[0].count('.');
        for ext, ext_ in sorted(settings.EXTENSIONS, cmp=s_cmp):
            if re.match(".*\.%s$" % ext.replace('.', '\.'), domain):
                return ext
        return AttributeError('extention not found')

    @classmethod
    def split(cls, domain):
        ext = cls.get_extension(domain)
        name = re.sub("\.%s$" % ext.replace('.', '\.'), '', domain) 
        return name, ext


class NameServer(models.Model):
    """ Used for domain registration process """
    name = models.ForeignKey(Name)
    hostname = models.CharField(max_length=255)
    ip = models.IPAddressField(null=True, blank=True)
    
    def __unicode__(self):
        return str(self.hostname)   
        

@receiver(collect_related_objects_to_delete, sender=Name, dispatch_uid="zone.collect_zones")
def collect_zones(sender, **kwargs):
    """ For a given Name colect their related Zones for future deletion """
    name = kwargs['object']
    zone = name.get_zone()
    if zone:
        if zone.origin == "%s.%s" % (name.name, name.extension):
            if not Name in kwargs['related_collection'].keys():
                kwargs['related_collection'][Name] = []
            kwargs['related_collection'][Name].append(zone)
        else:
            if not Record in kwargs['related_collection'].keys():
                kwargs['related_collection'][Record] = []
            kwargs['related_collection'][Record].append(name.get_record())