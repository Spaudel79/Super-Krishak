import os

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from taggit.managers import TaggableManager
from versatileimagefield.fields import VersatileImageField

from super_krishak.core.models import TimeStampAbstractModel

# Create your models here.

REACTIONS = [(1, "useless"), (2, "good"), (3, "informative")]
SHARED = [(1, "facebook"), (2, "twitter"), (3, "reddit")]


def upload_path(instance, filename):
    return os.path.join(
        instance.__class__.__name__, str(instance.created_at.microsecond), filename
    )


class Gallery(TimeStampAbstractModel):
    picture = VersatileImageField(
        "Image",
        upload_to=upload_path,
        blank=True,
    )
    updated_at = None

    class Meta:
        ordering = ["created_at"]


class Articles(TimeStampAbstractModel):

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="articles",
    )

    title = models.CharField(max_length=255, blank=True)
    tags = TaggableManager()
    image_files = models.ManyToManyField(Gallery, related_name="articles")

    content = models.TextField(blank=True)

    video_content = models.URLField(max_length=255, blank=True)

    post_views = models.IntegerField(default=0)

    unique_visitors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="article_views"
    )

    launch_date = models.DateField(null=True)

    def __str__(self):
        return self.title

    @property
    def slug_of_title(self):

        slug = slugify(self.title)
        return slug

    @property
    def reacts_count(self):
        return self.article_reacts.all().count()

    class Meta:
        ordering = ["-created_at"]


class Reactions(TimeStampAbstractModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name="user_reacts",
    )
    article = models.ForeignKey(
        Articles,
        on_delete=models.CASCADE,
        null=True,
        related_name="article_reacts",
    )
    reacts = models.CharField(max_length=1, choices=REACTIONS, default="")
    updated_at = None

    def __str__(self):
        return "Reacted by {} on {} and reaction is {}".format(
            self.user.name, self.article.title, self.reacts
        )


class Shares(TimeStampAbstractModel):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name="user_shares",
    )

    article = models.ForeignKey(
        Articles,
        on_delete=models.CASCADE,
        null=True,
        related_name="article_shares",
    )

    fb_counts = models.IntegerField(default=0)

    twitter_counts = models.IntegerField(default=0)

    reddit_counts = models.IntegerField(default=0)

    last_shared_on = models.CharField(max_length=1, choices=SHARED, default="")

    def __str__(self):
        return "Shared {} by {}".format(
            self.article.title,
            self.user.name,
        )
