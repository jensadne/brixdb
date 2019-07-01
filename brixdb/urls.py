from django.conf.urls import url

from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'set', views.SetViewSet, basename='set')
router.register(r'element', views.ElementViewSet, basename='element')
router.register(r'colour', views.ColourViewSet, basename='colour')
router.register(r'part', views.PartViewSet, basename='part')
urlpatterns = router.urls
