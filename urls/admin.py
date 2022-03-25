from django.urls import include, path
from rest_framework.routers import DefaultRouter

from super_krishak.articles.api.v1.views import admin

app_name = "articles"
router = DefaultRouter()
router.register(r"", admin.ArticlesView)

urlpatterns = [
    path("<int:pk>/", admin.ArticlesView.as_view({"get": "list", "delete": "destroy"})),
    path("reactions/<int:pk>/", admin.ReactionsDetailView.as_view({"get": "list"})),
    path(
        "reactions/<int:pk>/csv/", admin.ReactionsDetailView.as_view({"get": "get_csv"})
    ),
    path("shares/<int:pk>/", admin.SharesView.as_view({"get": "list"})),
    path("shares/<int:pk>/csv/", admin.SharesView.as_view({"get": "get_csv"})),
]


urlpatterns += [path("", include(router.urls))]
