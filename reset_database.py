import requests
import json
from application import db
# from sqlalchemy.orm.session import close_all_sessions
from application.settingssecrets import JUDGE0_AUTHN_TOKEN, JUDGE0_AUTHZ_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from application.models.general import *
import boto3

# db.session.close()

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
bucket = s3.Bucket('code-execution-grade-10')

bucket.objects.all().delete()

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
    db.session.add(lang_db)

for s in status:
    status_db = Status(number=s['id'], name=s['description'])
    db.session.add(status_db)

# user1 = User(email='vishnupavan.satish@gmail.com',
#              password='$2y$12$cKun4wx7p.lgL3px1qYesOlRZXKEsmZGhl69N04K3NJZyndNDuvRm', name='Vishnu S.')
#
# db.session.add(user1)

db.session.commit()

db.session.close()
