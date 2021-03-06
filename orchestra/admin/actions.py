from django.contrib import admin
from django.core.mail import send_mass_mail
from django.shortcuts import render
from django.utils.translation import ungettext, ugettext_lazy as _

from .. import settings

from .forms import SendEmailForm


class SendEmail(object):
    """ Form wizard for billing orders admin action """
    short_description = _("Send email")
    form = SendEmailForm
    template = 'admin/orchestra/generic_confirmation.html'
    default_from = settings.ORCHESTRA_DEFAULT_SUPPORT_FROM_EMAIL
    __name__ = 'semd_email'
    
    def __call__(self, modeladmin, request, queryset):
        """ make this monster behave like a function """
        self.modeladmin = modeladmin
        self.queryset = queryset
        self.opts = modeladmin.model._meta
        app_label = self.opts.app_label
        self.context = {
            'action_name': _("Send email"),
            'action_value': self.__name__,
            'opts': self.opts,
            'app_label': app_label,
            'queryset': queryset,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }
        return self.write_email(request)
    
    def write_email(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        initial={
            'email_from': self.default_from,
            'to': ' '.join(self.get_queryset_emails())
        }
        form = self.form(initial=initial)
        if request.POST.get('post'):
            form = self.form(request.POST, initial=initial)
            if form.is_valid():
                options = {
                    'email_from': form.cleaned_data['email_from'],
                    'extra_to': form.cleaned_data['extra_to'],
                    'subject': form.cleaned_data['subject'],
                    'message': form.cleaned_data['message'],
                    
                }
                return self.confirm_email(request, **options)
        opts = self.modeladmin.model._meta
        app_label = opts.app_label
        self.context.update({
            'title': _("Send e-mail to %s") % self.opts.verbose_name_plural,
            'content_title': "",
            'form': form,
            'submit_value': _("Continue"),
        })
        # Display confirmation page
        return render(request, self.template, self.context)
    
    def get_queryset_emails(self):
        return self.queryset.values_list('email', flat=True)
    
    def confirm_email(self, request, **options):
        email_from = options['email_from']
        extra_to = options['extra_to']
        subject = options['subject']
        message = options['message']
        # The user has already confirmed
        if request.POST.get('post') == 'email_confirmation':
            emails = []
            num = 0
            for email in self.get_queryset_emails():
                emails.append((subject, message, email_from, [email]))
                num += 1
            if extra_to:
                emails.append((subject, message, email_from, extra_to))
            send_mass_mail(emails, fail_silently=False)
            msg = ungettext(
                _("Message has been sent to one %s.") % self.opts.verbose_name_plural,
                _("Message has been sent to %i %s.") % (num, self.opts.verbose_name_plural),
                num
            )
            self.modeladmin.message_user(request, msg)
            return None
        
        form = self.form(initial={
            'email_from': email_from,
            'extra_to': ', '.join(extra_to),
            'subject': subject,
            'message': message
        })
        self.context.update({
            'title': _("Are you sure?"),
            'content_message': _(
                "Are you sure you want to send the following message to the following %s?"
            ) % self.opts.verbose_name_plural,
            'display_objects': ["%s (%s)" % (contact, contact.email) for contact in self.queryset],
            'form': form,
            'subject': subject,
            'message': message,
            'post_value': 'email_confirmation',
        })
        # Display the confirmation page
        return render(request, self.template, self.context)
