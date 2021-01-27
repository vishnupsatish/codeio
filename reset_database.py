import datetime as dt
import requests
import json
from application import db
from application.settingssecrets import JUDGE0_AUTHN_TOKEN, JUDGE0_AUTHZ_TOKEN
from application.models.general import *
import boto3


s3 = boto3.resource('s3')
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


user1 = User(username='vishnu', email='vishnupavan.satish@gmail.com',
             password='$2y$12$cKun4wx7p.lgL3px1qYesOlRZXKEsmZGhl69N04K3NJZyndNDuvRm', name='Vishnu S.')

db.session.add(user1)

db.session.commit()
