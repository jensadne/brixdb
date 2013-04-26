from django.conf.urls import patterns, url


urlpatterns = patterns('brixdb.views',
    url('^part/(?P<number>\w+)/$', 'part_index', name='part-detail'),

)
