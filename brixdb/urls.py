from django.conf.urls import url

from . import views


# TODO: get rid of these
urlpatterns = [
    url('^part/(?P<number>\w+)/$', views.part_index, name='part-detail'),
    url('^set/(?P<slug>.+)/$', views.SetView.as_view(), name='set-detail'),

    url(r'^colour/(?P<slug>.+)/not-owned/$', views.ColourDetail.as_view(), {'owned': False}, name='colour-not-owned'),
    url(r'^colour/(?P<slug>.+)/$', views.ColourDetail.as_view(), name='colour-detail'),
]
