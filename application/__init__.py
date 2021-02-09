import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from application.settingssecrets import MAIL_EMAIL, MAIL_PASSWORD
from flask_mail import Mail
from celery import Celery

from itsdangerous import URLSafeTimedSerializer

# Initialize Flask and extensions, such as Flask_SQLAlchemy, Flask_Login, etc.
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE')
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'teacher_login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'You must be logged in to view that page.'

# Initialize Celery, the background task manager
app.config['CELERY_BROKER_URL'] = os.environ.get('CELERY_BROKER_URL')
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Initialize Flask-Mail, used for sending confirmation emails
app.config['MAIL_SERVER'] = 'smtp.codeio.tech'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = MAIL_EMAIL
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
mail = Mail(app)

# Initialize Flask-Limiter
app.config['RATELIMIT_STORAGE_URL'] = 'redis://localhost:6379/0'
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=['400 per day', '100 per hour', '20 per minute']
)

# Initialize the timed serializer, used for confirming a user's email
serializer = URLSafeTimedSerializer(os.environ.get('SECRET_KEY'))

# Import each route from all initializations have been finished
from application.routes import student, teacher, errors
