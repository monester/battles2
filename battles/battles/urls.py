from django.urls import path
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from scheduler.views import FetchClanDataView
from .views import IndexView

urlpatterns = [
    path('', IndexView.as_view(), name='home'),
    path('update/<int:clan_id>-<slug:clan_tag>', FetchClanDataView.as_view()),
    path('update/<slug:clan_tag>', FetchClanDataView.as_view()),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
