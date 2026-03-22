from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('network/', include('network.urls')),
    path('trips/', include('trips.urls')),
    path('api/', include('trips.api_urls')),
    path('', RedirectView.as_view(url='/trips/', permanent=False)),
]
