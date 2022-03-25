from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    name = "super_krishak.articles"

    def ready(self):
        from . import signals  # noqa F401
