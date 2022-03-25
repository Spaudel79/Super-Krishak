from datetime import datetime, time, timedelta

import pytz
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from super_krishak.articles.models import Articles
from super_krishak.notifications.tasks import notify_users


@receiver(post_save, sender=Articles)
def send_notification(sender, instance, created, **kwargs):
    if created:
        if timezone.now().date() == instance.launch_date:
            start = timezone.now() + timedelta(seconds=5)
        else:
            start_time = time(0)
            start = datetime.combine(instance.launch_date, start_time)
        notification_send_time = start
        zone = pytz.timezone(settings.TIME_ZONE)
        eta = notification_send_time.astimezone(zone)
        extra = {"type": "article", "article_id": instance.id}
        res = notify_users.schedule(("New article alert.", extra), eta=eta)
        res()
