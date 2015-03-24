# -*- coding: utf-8 -*-

from django.db import models
from django.db.models import Q


class PrivateTopicManager(models.Manager):
    """
    Custom private topic manager.
    """

    def get_private_topics_of_user(self, user_id):
        return super(PrivateTopicManager, self).get_queryset() \
            .filter(Q(participants__in=[user_id]) | Q(author=user_id)) \
            .select_related("author", "participants") \
            .distinct().order_by('-last_message__pubdate').all()
