# coding: utf-8

import itertools

from collections import OrderedDict
from django import template
from django.conf import settings

from zds.forum.models import Forum, Topic
from zds.tutorialv2.models.models_database import PublishedContent
from zds.utils.models import CategorySubCategory, Tag
from django.db.models import Count

register = template.Library()


@register.filter('top_categories')
def top_categories(user):
    cats = {}

    forums_pub = Forum.objects.filter(group__isnull=True).select_related("category").distinct().all()
    if user and user.is_authenticated():
        forums_prv = Forum\
            .objects\
            .filter(group__isnull=False, group__in=user.groups.all())\
            .select_related("category").distinct().all()
        forums = list(forums_pub | forums_prv)
    else:
        forums = list(forums_pub)

    for forum in forums:
        key = forum.category.title
        if key in cats:
            cats[key].append(forum)
        else:
            cats[key] = [forum]

    tmp_tags = (Topic.objects
                .values_list('tags__pk', flat=True)
                .distinct()
                .filter(forum__in=forums, tags__isnull=False)
                .annotate(nb_tags=Count("tags"))
                .order_by("-nb_tags")
                [:settings.ZDS_APP['forum']['top_tag_max'] + len(settings.ZDS_APP['forum']['top_tag_exclu'])])

    tags_not_filtered = Tag.objects.filter(pk__in=[pk for pk in tmp_tags])

    # Select tags that are not in the excluded list
    tags = []
    for tag in tags_not_filtered:
        if tag.title not in settings.ZDS_APP['forum']['top_tag_exclu'] \
                and len(tags) <= settings.ZDS_APP['forum']['top_tag_max']:
            tags.append(tag)

    return {"tags": tags, "categories": cats}


@register.filter('top_categories_content')
def top_categories_content(_type):
        """Get all the categories and their related subcategories associated with existing contents.
        The result is sorted by alphabetic order.

        :param _type: type of the content
        :type _type: str
        :return: a dictionary, with the title being the name of the category and the content a list of subcategories,
        Each of these are stored in a tuple of the form ``title, slug``.
        :rtype: OrderedDict
        """
        if _type:
            subcategories_contents = PublishedContent.objects\
                .filter(content_type=_type)\
                .values('content__subcategory').all()
        else:
            subcategories_contents = PublishedContent.objects\
                .values('content__subcategory').all()

        categories_from_subcategories = CategorySubCategory.objects\
            .filter(is_main=True)\
            .filter(subcategory__in=subcategories_contents)\
            .order_by('category__position', 'subcategory__title')\
            .select_related('subcategory', 'category')\
            .values('category__title', 'subcategory__title', 'subcategory__slug')\
            .all()

        categories = OrderedDict()

        for csc in categories_from_subcategories:
            key = csc['category__title']

            if key in categories:
                categories[key].append((csc['subcategory__title'], csc['subcategory__slug']))
            else:
                categories[key] = [(csc['subcategory__title'], csc['subcategory__slug'])]

        tgs = PublishedContent.objects\
            .values('content__tags', 'pk')\
            .select_related('content')\
            .distinct()\
            .filter(content__tags__isnull=False)

        cts = {}
        for key, group in itertools.groupby(tgs, lambda item: item["content__tags"]):
            for thing in group:
                if key in cts:
                    cts[key] += 1
                else:
                    cts[key] = 1

        cpt = 0
        top_tag = []
        sort_list = reversed(sorted(cts.iteritems(), key=lambda k_v: (k_v[1], k_v[0])))
        for key, value in sort_list:
            top_tag.append(key)
            cpt += 1
            if cpt >= settings.ZDS_APP['tutorial']['top_tag_max']:
                break

        tags = Tag.objects.filter(pk__in=top_tag)

        return {"tags": tags, "categories": categories}


@register.filter('auth_forum')
def auth_forum(forum, user):
    return forum.can_read(user)
