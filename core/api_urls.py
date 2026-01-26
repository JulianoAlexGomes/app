from rest_framework.routers import DefaultRouter
from .api import ClientViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='clients')

urlpatterns = router.urls
