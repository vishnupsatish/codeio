import datetime as dt
import requests
import json
from application import db
from application.settingssecrets import JUDGE0_AUTHN_TOKEN, JUDGE0_AUTHZ_TOKEN
from application.models.general import *

db.drop_all()
db.create_all()

base_url = 'https://judge0-fhwnc7.vishnus.me'

languages = requests.get(f'{base_url}/languages/', headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN})

languages = json.loads(languages.text)

for l in languages:
    l_id = l['id']
    l_name = l['name']
    lang_db = Language(number=l_id, name=l_name)
    db.session.add(lang_db)


user1 = User(username='vishnu', email='vishnupavan.satish@gmail.com',
             password='$2y$12$cKun4wx7p.lgL3px1qYesOlRZXKEsmZGhl69N04K3NJZyndNDuvRm', name='Vishnu S.')

db.session.add(user1)


# db.session.add_all(
#     [school, user1, user2, user3, announcement1, announcement1link1, announcement2, class1, schedule1, content1])
#
# db.session.commit()
db.session.commit()
