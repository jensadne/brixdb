from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic.base import TemplateView


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='frontpage.html'), name='main-index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('brixdb.urls')),

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
