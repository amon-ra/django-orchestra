import sys

from orchestra.conf.base_settings import *


DEBUG = True

TEMPLATE_DEBUG = True

CELERY_SEND_TASK_ERROR_EMAILS = False

# When DEBUG is enabled Django appends every executed SQL statement to django.db.connection.queries
# this will grow unbounded in a long running process environment like celeryd
if set(('celeryd', 'celeryev', 'celerycam', 'celerybeat')).intersection(sys.argv):
    DEBUG = False

# Django debug toolbar
INSTALLED_APPS += (
    'debug_toolbar',
    'django_nose',
)
MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
INTERNAL_IPS = (
    '127.0.0.1',
    '10.0.3.1',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
