from rest_framework import serializers
from taggit.models import Tag
from taggit_serializer.serializers import TaggitSerializer, TagListSerializerField

from super_krishak.articles.models import Articles, Gallery, Reactions, Shares
from super_krishak.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "address", "mobile"]


class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ["id", "picture", "created_at"]


class ReactionSerializer(serializers.ModelSerializer):

    user = serializers.PrimaryKeyRelatedField(read_only=True, required=False)

    class Meta:
        model = Reactions
        fields = ["id", "user", "article", "reacts"]


class ReactionDetailSerializer(serializers.ModelSerializer):

    user = UserSerializer()

    class Meta:
        model = Reactions
        fields = ["id", "user", "reacts", "created_at"]


class ShareSerializer(serializers.ModelSerializer):

    user = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    fb_counts = serializers.IntegerField(required=False)
    twitter_counts = serializers.IntegerField(required=False)
    reddit_counts = serializers.IntegerField(required=False)
    last_shared_on = serializers.IntegerField(required=False)
    last_shared_at = serializers.DateTimeField(source="updated_at", required=False)

    class Meta:
        model = Shares
        fields = [
            "id",
            "user",
            "article",
            "fb_counts",
            "twitter_counts",
            "reddit_counts",
            "last_shared_on",
            "last_shared_at",
        ]


class ShareDetailSerializer(serializers.ModelSerializer):

    user = UserSerializer()
    last_shared_at = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Shares
        fields = ["id", "user", "last_shared_on", "last_shared_at"]


class ArticleSerializer(TaggitSerializer, serializers.ModelSerializer):

    tags = TagListSerializerField(required=False)
    image_files = GallerySerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(source="creator")

    total_shares = serializers.FloatField(read_only=True)
    total_reacts = serializers.FloatField(read_only=True)
    bad_reacts = serializers.FloatField(read_only=True)
    good_reacts = serializers.FloatField(read_only=True)
    informative_reacts = serializers.FloatField(read_only=True)
    launch_date = serializers.DateField(required=True)

    class Meta:
        model = Articles
        fields = [
            "id",
            "user",
            "title",
            "tags",
            "image_files",
            "content",
            "video_content",
            "post_views",
            "launch_date",
            "total_shares",
            "total_reacts",
            "bad_reacts",
            "good_reacts",
            "informative_reacts",
        ]

        extra_kwargs = {
            "image_files": {
                "required": False,
            }
        }

    def create(self, validated_data):
        tags = validated_data.pop("tags", None)
        instance = super(ArticleSerializer, self).create(validated_data)
        if tags is not None:
            for tag in tags:
                instance.tags.add(tag)
        instance.save()
        return instance


class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["name"]
