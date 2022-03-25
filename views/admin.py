import csv

from django.db.models import Case, Count, F, FloatField, Q, Sum, Value
from django.db.models.expressions import When
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from super_krishak.articles.api.v1.serializers.admin import (
    ArticleSerializer,
    ReactionDetailSerializer,
    ShareDetailSerializer,
)
from super_krishak.articles.models import Articles, Gallery, Reactions, Shares
from super_krishak.core.pagination import DynamicPageSizePagination


def permission_denied():
    message = "This Article belongs to another creator."
    raise PermissionDenied(message)


dummy_divisor = 0.0


def check(result, divisor):

    return Case(
        When(
            **{
                divisor: 0.0,
                "then": Value(dummy_divisor, FloatField()),
            }
        ),
        default=result,
        output_field=FloatField(),
    )


class ArticlesView(viewsets.ModelViewSet):
    queryset = Articles.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        user = request.user
        images_list = request.FILES.getlist("image_files")
        if images_list:
            request.data.pop("image_files")
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(creator=user)
                id = serializer.data["id"]
                article_obj = get_object_or_404(Articles, id=id)

                for image in images_list:
                    image_content = Gallery.objects.create(picture=image)
                    article_obj.image_files.add(image_content)

                data = {
                    "id": article_obj.id,
                    "user": request.user,
                    "title": article_obj.title,
                    "tags": article_obj.tags,
                    "image_files": article_obj.image_files,
                    "video_content": article_obj.video_content,
                    "post_views": article_obj.post_views,
                    "launch_date": article_obj.launch_date,
                }
                serializer = self.serializer_class(data)
                return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            data = request.data
            serializer = self.serializer_class(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        qs = (
            Articles.objects.select_related("creator")
            .prefetch_related(
                "image_files",
                "tags",
            )
            .annotate(
                total_shares=Sum(
                    F("article_shares__fb_counts")
                    + F("article_shares__twitter_counts")
                    + F("article_shares__reddit_counts"),
                    output_field=FloatField(),
                ),
                total_reacts=Count("article_reacts") / 1.0,
                bad_reacts=Coalesce(
                    check(
                        100.0
                        * Count("article_reacts", filter=Q(article_reacts__reacts=1))
                        / Count("article_reacts")
                        / 1.0,
                        "total_reacts",
                    ),
                    0.0,
                    output_field=FloatField(),
                ),
                good_reacts=Coalesce(
                    check(
                        100.0
                        * Count("article_reacts", filter=Q(article_reacts__reacts=2))
                        / Count("article_reacts")
                        / 1.0,
                        "total_reacts",
                    ),
                    0.0,
                    output_field=FloatField(),
                ),
                informative_reacts=Coalesce(
                    check(
                        100.0
                        * Count("article_reacts", filter=Q(article_reacts__reacts=3))
                        / Count("article_reacts")
                        / 1.0,
                        "total_reacts",
                    ),
                    0.0,
                    output_field=FloatField(),
                ),
            )
        )

        query = self.request.GET.get("ordering", None)

        if query:
            if query == "reacts_count":
                query = "total_reacts"
            elif query and query == "-reacts_count":
                query = "-total_reacts"
            qs = qs.order_by(query)
        return qs

    def list(self, request, *args, **kwargs):
        id = kwargs.get("pk")

        if id is not None:
            article = self.get_queryset().get(id=id)
            serializer = self.serializer_class(article)
            return Response(serializer.data, status=status.HTTP_200_OK)

        else:
            additional_field = {
                "total_post_views": Articles.objects.aggregate(
                    total_views=Sum("post_views")
                ),
                "total_unique_views": Articles.objects.aggregate(
                    unique_visits=Count("unique_visitors")
                ),
            }

            paginator = DynamicPageSizePagination()
            result_page = paginator.paginate_queryset(self.get_queryset(), request)
            serializer = self.serializer_class(result_page, many=True)
            return paginator.get_paginated_response([additional_field, serializer.data])

    def is_creator(self, article_id):
        """
        validation function which checks whether the article belongs to the
        current logged in user.
        """

        user = self.request.user
        article_id = article_id
        article_ids = list(
            Articles.objects.filter(creator=user).values_list("id", flat=True)
        )

        if article_id in article_ids:
            return True
        else:
            raise PermissionDenied(permission_denied())

    def destroy(self, request, *args, **kwargs):

        id = kwargs.get("pk")
        article = get_object_or_404(Articles, id=id)

        if self.is_creator(id):
            article.image_files.all().delete()
            article.delete()

            return Response(
                {
                    "message": "Article has been successfully deleted.",
                },
                status=status.HTTP_200_OK,
            )
        return Response(status=status.HTTP_400_BAD_REQUEST)


class ReactionsDetailView(viewsets.ModelViewSet):
    queryset = Reactions.objects.all()
    serializer_class = ReactionDetailSerializer
    permission_classes = [IsAdminUser]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == "get_csv":
            return []
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):

        order_query = self.request.GET.get("ordering", None)
        search_query = self.request.GET.get("search", None)

        if search_query is not None:
            queryset = Reactions.objects.filter(
                Q(user__name__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(user__address__icontains=search_query)
                | Q(user__mobile__icontains=search_query)
            ).distinct()

            if order_query is not None:
                return queryset.order_by(order_query)

            else:
                return queryset

        elif order_query is not None:

            queryset = Reactions.objects.all().order_by(order_query)
            return queryset

        else:
            return Reactions.objects.all()

    def list(self, request, *args, **kwargs):

        id = self.kwargs.get("pk")
        queryset = self.get_queryset().filter(article=id)

        paginator = DynamicPageSizePagination()
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = ReactionDetailSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_csv(self, request, pk=None):

        article_id = pk
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="reactions.csv"'
        writer = csv.writer(response)
        queryset = self.get_queryset().filter(article=article_id)
        writer.writerow(
            [
                "Name",
                "Address",
                "Reaction",
                "Email",
                "Contact No.",
                "Reacted Date & Time",
            ]
        )

        for q in queryset:
            writer.writerow(
                [
                    q.user.name,
                    q.user.address,
                    q.reacts,
                    q.user.email,
                    q.user.mobile,
                    q.created_at,
                ]
            )
        return response


class SharesView(viewsets.ModelViewSet):
    queryset = Shares.objects.all()
    serializer_class = ShareDetailSerializer
    permission_classes = [IsAdminUser]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == "get_csv":
            return []
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):

        order_query = self.request.GET.get("ordering", None)
        search_query = self.request.GET.get("search", None)

        if search_query is not None:
            queryset = Shares.objects.filter(
                Q(user__name__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(user__address__icontains=search_query)
                | Q(user__mobile__icontains=search_query)
            ).distinct()

            if order_query is not None:
                return queryset.order_by(order_query)

            else:
                return queryset

        elif order_query is not None:

            queryset = Shares.objects.all().order_by(order_query)
            return queryset

        else:
            return Shares.objects.all()

    def list(self, request, *args, **kwargs):

        id = self.kwargs.get("pk")
        queryset = self.get_queryset().filter(article=id)

        paginator = DynamicPageSizePagination()
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = ShareDetailSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_csv(self, request, pk=None):

        article_id = pk
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="shares.csv"'
        writer = csv.writer(response)
        queryset = self.get_queryset().filter(article=article_id)
        writer.writerow(
            ["Name", "Address", "Media", "Email", "Contact No.", "Reacted Date & Time"]
        )

        for q in queryset:
            if q.last_shared_on == 1:
                media = "facebook"
            elif q.last_shared_on == 2:
                media = "twitter"
            else:
                media = "reddit"

            writer.writerow(
                [
                    q.user.name,
                    q.user.address,
                    media,
                    q.user.email,
                    q.user.mobile,
                    q.created_at,
                ]
            )
        return response
