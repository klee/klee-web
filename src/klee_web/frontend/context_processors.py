from django.conf import settings


def global_vars(request):
    return {'dist': '{}frontend/dist/'.format(settings.STATIC_URL)}
