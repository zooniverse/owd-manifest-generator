import csv
import datetime
import io
import json
import os
import re

import boto3
import progressbar

from PIL import Image


DATA_PATH = os.environ.get('DATA_PATH', os.path.join('/', 'data')).rstrip('/')
DATA_PREFIX = os.environ.get('DATA_PREFIX', '').rstrip('/')
DIARY_METADATA_FILE = os.environ.get(
    'DIARY_METADATA_FILE',
    os.path.join('/', 'diaries.tsv'),
)
EXTRA_METADATA_FILE = os.environ.get(
    'EXTRA_METADATA_FILE',
    os.path.join('/', 'extra.tsv'),
)

DIARY_METADATA_COLUMNS = (
    'dir1',
    'dir2',
    'id',
    'name',
)

IMAGE_REGEX = r'(?P<page_number>[0-9]+)\.jpg'

OUT_IMAGE_SIZE = (1400, 1400)
OUT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET', 'zooniverse-data')
UPLOAD_PREFIX = os.environ.get(
    'UPLOAD_PREFIX', 'project_data/owd/manifests'
).strip('/')

def parse_date(date_str):
    return datetime.date(
        year=int(date_str[:4]),
        month=int(date_str[4:6]),
        day=int(date_str[6:8]),
    )


diaries = {}

with open(DIARY_METADATA_FILE) as diary_file:
    diary_reader = csv.reader(diary_file, delimiter='\t')

    for diary in diary_reader:
        diary = dict(zip(DIARY_METADATA_COLUMNS, diary))
        diaries[diary['id']] = diary

with open(EXTRA_METADATA_FILE, encoding='utf-8-sig') as extra_file:
    extra_reader = csv.DictReader(extra_file, delimiter='\t')

    for diary in extra_reader:
        if diary['IAID'] not in diaries:
            continue

        diary['CoveringFromDate'] = parse_date(diary['CoveringFromDate'])
        diary['CoveringToDate'] = parse_date(diary['CoveringToDate'])

        diaries[diary['IAID']].update(diary)

json_out = []
s3_client = boto3.client('s3')

total_diaries = len(diaries)

for diary_n, (diary_key, diary) in enumerate(diaries.items(), start=1):
    if 'IAID' not in diary:
        print('Warning: Diary {} has incomplete metadata. Skipping'.format(
            diary_key
        ))
        continue
    diary_prefix = os.path.join(
        DATA_PREFIX,
        diary['dir1'],
        diary['dir2']
    )
    diary_dir = os.path.join(DATA_PATH, diary_prefix)
    diary_upload_path = '{}/{}'.format(
        UPLOAD_PREFIX,
        diary_prefix,
    )
    json_out.append({
        'type': 'group',
        'name': diary['name'],
        'metadata': {
            'id': diary['IAID'],
            'source': diary_prefix,
            'year': diary['CoveringFromDate'].year,
            'diary_number': int(diary['dir2']),
            'start_date': diary['CoveringFromDate'].strftime(OUT_DATE_FORMAT),
            'end_date': diary['CoveringToDate'].strftime(OUT_DATE_FORMAT),
        },
    })
    processed_images = [
        s3_object['Key'] for s3_object in s3_client.list_objects_v2(
            Bucket=UPLOAD_BUCKET,
            Prefix='{}/{}/'.format(
                UPLOAD_PREFIX,
                diary_prefix,
            )
        ).get('Contents', [])
    ]
    with progressbar.ProgressBar(
        widgets=[
            progressbar.FormatLabel('Processing {} ({} of {})'.format(
                diary['IAID'],
                diary_n,
                total_diaries,
            )),
            ' ',
            progressbar.Bar(),
            progressbar.Percentage(),
            ' ',
            progressbar.ETA(),
        ]
    ) as bar:
        for file_name in bar(os.listdir(diary_dir)):
            file_match = re.match(IMAGE_REGEX, file_name)
            if not file_match:
                continue

            upload_key = '{}/{}'.format(
                diary_upload_path,
                file_name,
            )
            upload_url = 'https://s3.amazonaws.com/{}/{}'.format(
                UPLOAD_BUCKET,
                upload_key
            )

            with open(os.path.join(diary_dir, file_name), 'rb') as image_f:
                subject_image = Image.open(image_f)
                original_width, original_height = subject_image.size
                if upload_key in processed_images:
                    resized_image = Image.open(s3_client.get_object(
                        Bucket=UPLOAD_BUCKET,
                        Key=upload_key,
                    )['Body'])
                    new_width, new_height = resized_image.size
                else:
                    subject_image.thumbnail(OUT_IMAGE_SIZE)
                    new_width, new_height = subject_image.size

                    with io.BytesIO() as image_data:
                        subject_image.save(image_data, format='jpeg')
                        s3_client.put_object(
                            ACL='public-read',
                            Body=image_data.getvalue(),
                            Bucket=UPLOAD_BUCKET,
                            Key=upload_key,
                        )

            json_out.append({
                'type': 'subject',
                'location': {
                    'standard': upload_url,
                },
                'group_name': diary['name'],
                'metadata': {
                    'tna_id': diary['IAID'],
                    'original_size': {
                        'width': original_width,
                        'height': original_height,
                    },
                    'aspect_ratio': original_width / float(original_height),
                    'size': {
                        'width': new_width,
                        'height': new_height,
                    },
                    'file_name': os.path.join(diary_prefix, file_name),
                    'page_number': int(file_match.group('page_number')),
                },
            })

s3_client.put_object(
    ACL='public-read',
    Body=json.dumps(json_out),
    Bucket=UPLOAD_BUCKET,
    Key='{}/manifest.json'.format(UPLOAD_PREFIX),
)
