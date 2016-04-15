from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns('brixdb.views',
    url('^part/(?P<number>\w+)/$', 'part_index', name='part-detail'),
    url('^set/(?P<slug>.+)/$', views.SetView.as_view(), name='set-detail'),

    url(r'^colour/(?P<slug>.+)/not-owned/$', views.ColourDetail.as_view(), {'owned': False}, name='colour-not-owned'),
    url(r'^colour/(?P<slug>.+)/$', views.ColourDetail.as_view(), name='colour-detail'),
)
