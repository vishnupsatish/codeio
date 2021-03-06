import requests
import json
from application import db
from application.settingssecrets import JUDGE0_AUTHN_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME
from application.models.general import *
import boto3

try:
    db.session.commit()
except Exception as e:
    db.session.rollback()


status = [
    {
        "id": 1,
        "description": "In Queue"
    },
    {
        "id": 2,
        "description": "Processing"
    },
    {
        "id": 3,
        "description": "Accepted"
    },
    {
        "id": 4,
        "description": "Wrong Answer"
    },
    {
        "id": 5,
        "description": "Time Limit Exceeded"
    },
    {
        "id": 6,
        "description": "Compilation Error"
    },
    {
        "id": 7,
        "description": "Runtime Error (SIGSEGV)"
    },
    {
        "id": 8,
        "description": "Runtime Error (SIGXFSZ)"
    },
    {
        "id": 9,
        "description": "Runtime Error (SIGFPE)"
    },
    {
        "id": 10,
        "description": "Runtime Error (SIGABRT)"
    },
    {
        "id": 11,
        "description": "Runtime Error (NZEC)"
    },
    {
        "id": 12,
        "description": "Runtime Error (Other)"
    },
    {
        "id": 13,
        "description": "Internal Error"
    },
    {
        "id": 14,
        "description": "Exec Format Error"
    }
]

s3 = boto3.resource('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
bucket = s3.Bucket(AWS_BUCKET_NAME)

classes = Class_.query.all()

for class_ in classes:
    for problem in class_.problems:
        for input_file in problem.input_files:
            s3.Object(AWS_BUCKET_NAME, input_file.file_path).delete()
        for output_file in problem.output_files:
            s3.Object(AWS_BUCKET_NAME, output_file.file_path).delete()
        for submission in problem.submissions:
            s3.Object(AWS_BUCKET_NAME, submission.file_path).delete()


db.session.remove()

db.drop_all()
db.create_all()

base_url = 'https://judge0-fhwnc7.vishnus.me'

languages = requests.get(f'{base_url}/languages/', headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN})

languages = json.loads(languages.text)

for l in languages:
    l_id = l['id']
    if int(l_id) == 89:
        continue
    l_name = l['name']
    lang = requests.get(f'{base_url}/languages/{l_id}', headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN})
    lang = json.loads(lang.text)
    l_file_ext = lang['source_file'].split('.')[-1]
    lang_db = Language(number=l_id, name=l_name, file_extension=l_file_ext)
    if l_id == 49 or l_id == 50 or l_id == 48 or l_id == 75:
        lang_db.short_name = 'c'
    elif l_id == 71:
        lang_db.short_name = 'python'
    elif l_id == 52 or l_id == 53 or l_id == 54 or l_id == 76:
        lang_db.short_name = 'cc'
    elif l_id == 51:
        lang_db.short_name = 'csharp'
    elif l_id == 67:
        lang_db.short_name = 'pascal'
    elif l_id == 62:
        lang_db.short_name = 'java'
    elif l_id == 55:
        lang_db.short_name = 'lisp'
    elif l_id == 61:
        lang_db.short_name = 'haskell'
    elif l_id == 59:
        lang_db.short_name = 'fortran'
    elif l_id == 69:
        lang_db.short_name = 'prolog'
    elif l_id == 63:
        lang_db.short_name = 'javascript'
    elif l_id == 84:
        lang_db.short_name = 'vb'

    db.session.add(lang_db)

for s in status:
    status_db = Status(number=s['id'], name=s['description'])
    db.session.add(status_db)


db.session.commit()

db.session.close()
