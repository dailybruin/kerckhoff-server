from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path, reverse_lazy
from django.views.generic.base import RedirectView
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls
from rest_framework.permissions import AllowAny
from rest_framework_nested.routers import NestedSimpleRouter

from .users.urls import urlpatterns as auth_urlpatterns
from .users.views import UserCreateViewSet, UserViewSet
from .packages.views import PackageSetViewSet, PackageSetCreateAndListViewSet, PackageViewSet, \
    PackageCreateAndListViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"users", UserCreateViewSet)
router.register(r"package-sets", PackageSetViewSet)
router.register(r"package-sets", PackageSetCreateAndListViewSet)

package_set_router = NestedSimpleRouter(router, r'package-sets', lookup='package_set')
package_set_router.register(r'packages', PackageViewSet, base_name='package-sets_packages')
package_set_router.register(r'packages', PackageCreateAndListViewSet, base_name="package-sets_packages")

urlpatterns = [
                  path("admin/", admin.site.urls),
                  path("api/v1/docs/",
                       include_docs_urls(title="Kerckhoff REST API (v1)", permission_classes=[AllowAny, ])),
                  path("api/v1/", include(router.urls)),
                  path("api/v1/", include(package_set_router.urls)),
                  path("api-oauth/", include(auth_urlpatterns)),
                  path("api-token-auth/", views.obtain_auth_token),
                  path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
                  # the 'api-root' from django rest-frameworks default router
                  # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
                  re_path(r"^$", RedirectView.as_view(url=reverse_lazy("api-root"), permanent=False)),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
