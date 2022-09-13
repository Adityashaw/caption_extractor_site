from datetime import datetime
from django.conf import settings
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute, NumberAttribute,
    UnicodeAttribute, UTCDateTimeAttribute
)
from pynamodb.models import Model


class Subtitle(MapAttribute):
    start_time = NumberAttribute()
    end_time = NumberAttribute()
    text = UnicodeAttribute()


class Video(Model):
    class Meta:
        region = 'eu-central-1'
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
        table_name = 'videos'

    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    video_name = UnicodeAttribute(hash_key=True)
    subtitles = ListAttribute(of=Subtitle)
