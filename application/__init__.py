import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_admin import Admin

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nvhe7gnhbsy8yjhmdh4uidhyi58djh'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
admin = Admin(app, name='lms', template_mode='bootstrap3', url="/flask-admin")

from application.routes import student, teacher