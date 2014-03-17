from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns('brixdb.views',
    url('^part/(?P<number>\w+)/$', 'part_index', name='part-detail'),

    url(r'^colour/(?P<slug>.+)/$', views.ColourDetail.as_view(), name='colour-detail'),
)
