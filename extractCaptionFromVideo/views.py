from botocore.exceptions import ClientError
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from pymediainfo import MediaInfo
from thefuzz import fuzz

from .extract_cc import extract_cc
from .models import Video, Subtitle
import asyncio
import boto3
import os


def index(request):
    return render(
        request, "extractCaptionFromVideo/index.html"
    )


def s3_object_exists(s3_client, bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as ce:
        return int(ce.response['Error']['Code']) != 404
    return True


def cc_track_exists(file_obj):
    media_info = MediaInfo.parse(file_obj)
    if media_info.text_tracks:
        return True
    return False


def create_subtitles_from_srt_dict_array(my_json):
    subtitles = []
    for obj in my_json:
        subtitle = Subtitle(
            start_time=obj['startTime'],
            end_time=obj['endTime'],
            text=obj['ref'].lower()
        )
        subtitles.append(subtitle)
    return subtitles


async def upload_file_to_s3(s3_client, file_name):
    await asyncio.sleep(1)
    print("upload started")
    s3_client.upload_file(
        file_name,
        settings.AWS_STORAGE_BUCKET_NAME,
        file_name
    )
    os.remove(file_name)
    print("upload success")


async def upload_video(request):
    if request.method == 'POST':
        file_obj = request.FILES.get('videoInput')
        file_name = file_obj.name
        if file_obj.size > 105E6:
            messages.warning(
                request,
                'Max video size supported is 100MB. Kindly decrease and retry.'
            )
            return HttpResponseRedirect(reverse('uploadVideo'))

        if not cc_track_exists(file_obj):
            messages.error(
                request,
                'The video does not seem to have any closed captions.'
            )
            return HttpResponseRedirect(reverse('uploadVideo'))
        # above function call might have read the file object
        # and we need to seek it to original position
        file_obj.seek(0)
        subtitle_json = extract_cc(file_obj)

        # same reason as above
        file_obj.seek(0)
        # create Subtitle objects from srt dict array
        subtitles = create_subtitles_from_srt_dict_array(subtitle_json)

        # create s3 client object
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY
        )
        # check if file already exists on s3 and/or dynamodb
        if (Video.count(file_name)
                or s3_object_exists(
                    s3,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    file_name
                )):
            messages.info(
                request,
                'A video with this name already exists! '
                'Use search subtitles page for searching subtitles. '
                'If the existing video with same name is a different video, '
                'rename your video and try uploading again.'
            )
            return HttpResponseRedirect(reverse('uploadVideo'))

        # the file does not exist at both s3 and dynamodb
        # upload video to s3 and rest data to dynamodb
        video = Video(video_name=file_name, subtitles=subtitles)
        video.save()
        messages.success(
            request,
            'Video will be uploaded in background. '
            'It is currently being processed. '
            'You can go to search subtitles page to search for subtitles!'
        )
        # save the file temporarily to send to async s3 upload
        with open(file_name, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        loop = asyncio.get_event_loop()
        loop.create_task(upload_file_to_s3(s3, file_name))
        return HttpResponseRedirect(reverse('uploadVideo'))

    return render(
        request, "extractCaptionFromVideo/uploadVideo.html"
    )


def search_subtitles(request):
    if request.method == 'POST':
        video = Video.get(request.POST.get('videoName'))
        phrase = request.POST.get('searchString').lower()
        subtitles = video.subtitles
        result = []
        for subtitle in subtitles:
            ratio = fuzz.partial_ratio(subtitle.text, phrase)
            if ratio >= 75:
                subtitle = subtitle.as_dict()
                temp = dict({
                    'ratio': ratio,
                    'start_time': "{}".format(str(
                        timedelta(seconds=subtitle['start_time'])
                    )),
                    'end_time': "{}".format(str(
                        timedelta(seconds=subtitle['end_time'])
                    )),
                    'text': subtitle['text']
                })
                result.append(temp)
                print(temp)
        if not result:
            messages.info(
                request,
                'No subtitle found matching your search text. '
                'Please retry with different text.'
            )
        request.session['result'] = result
        return HttpResponseRedirect(reverse('searchSubtitles'))

    videos = Video.scan(attributes_to_get=['video_name'])
    if 'result' in request.session:
        result = request.session['result']
        del request.session['result']
    else:
        result = []
    return render(
        request,
        "extractCaptionFromVideo/searchSubtitles.html",
        {
            'videos': videos,
            'subtitles': result
        }
    )
