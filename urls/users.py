from django.urls import path

from super_krishak.articles.api.v1.views import users

app_name = "articles"


urlpatterns = [
    path("", users.ArticlesView.as_view()),
    path("tag/<slug:slug>/", users.ArticlesView.as_view()),
    path("<int:pk>/", users.ArticlesView.as_view()),
    path("reactions/", users.ReactionsView.as_view()),
    path("reactions/<int:pk>/", users.ReactionsView.as_view()),
    path("shares/", users.SharesView.as_view()),
    path("shares/<int:pk>/", users.SharesView.as_view()),
    path("tags/", users.TagsView.as_view()),
]
