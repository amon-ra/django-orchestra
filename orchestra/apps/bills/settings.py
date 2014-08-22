from django.conf import settings


BILLS_NUMBER_LENGTH = getattr(settings, 'BILLS_NUMBER_LENGTH', 4)

BILLS_INVOICE_NUMBER_PREFIX = getattr(settings, 'BILLS_INVOICE_NUMBER_PREFIX', 'I')

BILLS_AMENDMENT_INVOICE_NUMBER_PREFIX = getattr(settings, 'BILLS_AMENDMENT_INVOICE_NUMBER_PREFIX', 'A')

BILLS_FEE_NUMBER_PREFIX = getattr(settings, 'BILLS_FEE_NUMBER_PREFIX', 'F')

BILLS_AMENDMENT_FEE_NUMBER_PREFIX = getattr(settings, 'BILLS_AMENDMENT_FEE_NUMBER_PREFIX', 'B')

BILLS_BUDGET_NUMBER_PREFIX = getattr(settings, 'BILLS_BUDGET_NUMBER_PREFIX', 'Q')


BILLS_INVOICE_TEMPLATE = getattr(settings, 'BILLS_INVOICE_TEMPLATE', 'bills/microspective.html')


BILLS_CURRENCY = getattr(settings, 'BILLS_CURRENCY', 'euro')


BILLS_SELLER_PHONE = getattr(settings, 'BILLS_SELLER_PHONE', '111-112-11-222')

BILLS_SELLER_EMAIL = getattr(settings, 'BILLS_SELLER_EMAIL', 'sales@orchestra.lan')

BILLS_SELLER_WEBSITE = getattr(settings, 'BILLS_SELLER_WEBSITE', 'www.orchestra.lan')
