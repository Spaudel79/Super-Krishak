import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from taggit.models import Tag

from super_krishak.articles.api.v1.serializers.admin import (
    ArticleSerializer,
    ReactionSerializer,
    ShareSerializer,
    TagsSerializer,
)
from super_krishak.articles.models import Articles, Reactions, Shares
from super_krishak.core.pagination import DynamicPageSizePagination
from super_krishak.users.models import UserCoin


class ArticlesView(ListAPIView):
    queryset = Articles.objects.all().order_by("-created_at")
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        search = self.request.query_params.get("search", None)
        qs = (
            Articles.objects.filter(launch_date__lte=timezone.now())
            .select_related("creator")
            .prefetch_related("image_files", "tags")
            .order_by("-created_at")
        )

        if search is not None:
            search_query = search.split(",")

            q = Q()
            for query in search_query:
                q |= Q(tags__name__icontains=query) | Q(title__icontains=query)

            qs = qs.filter(q).distinct()

        return qs

    def get(self, request, *args, **kwargs):
        id = self.kwargs.get("pk")
        tag = self.kwargs.get("slug")
        qs = self.get_queryset()

        if id is not None:
            article = get_object_or_404(qs, id=id)

            """""
                increment of post views after a user views an article
            """
            article.post_views = article.post_views + 1
            article.save(update_fields=("post_views",))

            Articles.unique_visitors.through.objects.get_or_create(
                articles=article, user=self.request.user
            )

            serializer = ArticleSerializer(article)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            if tag is not None:
                qs = qs.filter(tags__name=tag)
            paginator = DynamicPageSizePagination()
            result_page = paginator.paginate_queryset(qs, request)
            serializer = ArticleSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)


class TagsView(ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get(self, request, *args, **kwargs):

        common_tags = Articles.tags.most_common()[:3]
        serializer = TagsSerializer(common_tags, many=True)
        return Response(serializer.data, status=200)


class ReactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = self.request.user
        article_id = self.kwargs.get("pk")
        reaction = request.data.get("reacts")

        try:
            previous_reaction = Reactions.objects.get(user=user, article=article_id)
        except ObjectDoesNotExist:
            previous_reaction = None

        if previous_reaction is not None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        else:
            data = {"user": user, "article": article_id, "reacts": reaction}
            serializer = ReactionSerializer(data=data)

            if serializer.is_valid():
                serializer.save(user=user)
                UserCoin.add_coins(user=user, coins_for="article")
                return Response(
                    {
                        "message": "You have reacted to the article.",
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors)

    def get(self, request, pk=None):
        """
        endpoint for insights on admin side and counts on detail page on user side
        """

        id = pk
        if id is not None:
            queryset = Reactions.objects.filter(article=id)
        else:
            queryset = Reactions.objects.all()

        queryset_count = queryset.count()

        if queryset_count == 0:

            data = {
                "total_reactions": 0,
                "total_bad_reactions": 0,
                "total_good_reactions": 0,
                "total_informative_reactions": 0,
            }

        else:

            informative_reactions = queryset.filter(reacts=3).count()
            good_reactions = queryset.filter(reacts=2).count()
            bad_reactions = queryset.filter(reacts=1).count()

            data = {
                "total_reactions": queryset_count,
                "total_bad_reactions": float(
                    "{:.2f}".format(100 * bad_reactions / queryset_count)
                ),
                "total_good_reactions": float(
                    "{:.2f}".format(100 * good_reactions / queryset_count)
                ),
                "total_informative_reactions": float(
                    "{:.2f}".format(100 * informative_reactions / queryset_count)
                ),
            }

        return Response(data, status=status.HTTP_200_OK)


class SharesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = self.request.user
        article_id = self.kwargs.get("pk")
        fb_counts = request.data.get("fb_counts", None)
        twitter_counts = request.data.get("twitter_counts", None)
        reddit_counts = request.data.get("reddit_counts", None)
        last_shared_on = request.data.get("last_shared_on")

        try:
            previous_share = Shares.objects.get(user=user, article=article_id)
        except ObjectDoesNotExist:
            previous_share = None

        if previous_share is not None:
            if fb_counts is not None:

                queryset = get_object_or_404(Shares, id=previous_share.id)

                """""
                    increment of facebook shares after a user shares an article on facebook
                """
                queryset.last_shared_on = last_shared_on
                queryset.updated_at = datetime.datetime.now()
                queryset.fb_counts = queryset.fb_counts + 1
                queryset.save(
                    update_fields=(
                        "fb_counts",
                        "last_shared_on",
                    )
                )

                serializer = ShareSerializer(queryset)
                return Response(serializer.data, status=status.HTTP_200_OK)

            elif twitter_counts is not None:

                queryset = get_object_or_404(Shares, id=previous_share.id)

                """""
                    increment of shares after a user shares an article on twitter
                """
                queryset.last_shared_on = last_shared_on
                queryset.updated_at = datetime.datetime.now()
                queryset.twitter_counts = queryset.twitter_counts + 1
                queryset.save(
                    update_fields=(
                        "twitter_counts",
                        "last_shared_on",
                    )
                )

                serializer = ShareSerializer(queryset)
                return Response(serializer.data, status=status.HTTP_200_OK)

            elif reddit_counts is not None:

                queryset = get_object_or_404(Shares, id=previous_share.id)

                """""
                    increment of shares after a user shares an article on reddit
                """
                queryset.last_shared_on = last_shared_on
                queryset.updated_at = datetime.datetime.now()
                queryset.reddit_counts = queryset.reddit_counts + 1
                queryset.save(
                    update_fields=(
                        "reddit_counts",
                        "last_shared_on",
                    )
                )

                serializer = ShareSerializer(queryset)
                return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            if fb_counts is not None:
                data = {
                    "user": user,
                    "article": article_id,
                    "fb_counts": fb_counts,
                    "last_shared_on": last_shared_on,
                }

            elif twitter_counts is not None:
                data = {
                    "user": user,
                    "article": article_id,
                    "twitter_counts": twitter_counts,
                    "last_shared_on": last_shared_on,
                }

            elif reddit_counts is not None:
                data = {
                    "user": user,
                    "article": article_id,
                    "reddit_counts": reddit_counts,
                    "last_shared_on": last_shared_on,
                }

            else:
                data = request.data

            serializer = ShareSerializer(data=data)

            if serializer.is_valid():
                serializer.save(user=user)
                return Response(serializer.data, status=200)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk=None):
        """
        endpoint for insights on admin side and counts on detail page on user side
        """

        id = pk
        if id is not None:
            queryset = Shares.objects.filter(article=id)
        else:
            queryset = Shares.objects.all()

        queryset_counts = queryset.count()

        if queryset_counts == 0:

            data = {
                "total_shares": 0,
                "total_fb_counts": 0,
                "total_twitter_counts": 0,
                "total_reddit_counts": 0,
            }

        else:
            dummy1 = 0
            dummy2 = 0
            dummy3 = 0

            for q in queryset:
                dummy1 = q.fb_counts + dummy1
                f_counts = dummy1
                dummy2 = q.twitter_counts + dummy2
                t_counts = dummy2
                dummy3 = q.reddit_counts + dummy3
                r_counts = dummy3

            total_shares = f_counts + t_counts + r_counts

            data = {
                "total_shares": total_shares,
                "total_facebook_shares": float(
                    "{:.2f}".format(f_counts * 100 / total_shares)
                ),
                "total_twitter_shares": float(
                    "{:.2f}".format(t_counts * 100 / total_shares)
                ),
                "total_reddit_shares": float(
                    "{:.f}".format(r_counts * 100 / total_shares)
                ),
            }
        return Response(data, status=status.HTTP_200_OK)
