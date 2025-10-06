from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

from hospital.views import HomeView

urlpatterns = [
                  path('apis/', include('api.urls')),
                  path('api-auth/', include('rest_framework.urls')),
                  path('finance/route/', include('finances.api.urls')),
                  path('hospital/route/', include('hospital.api.urls')),
                  path('human_ressource/route/', include('human_ressource.api.urls')),
                  path('laboratory/route/', include('laboratory.api.urls')),
                  path('logistic/route/', include('logistic.api.urls')),
                  path('pharmacy/route/', include('pharmacy.api.urls')),

                  path('home/dash', HomeView.as_view(), name="homeview"),

                  path('admin/', admin.site.urls),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
