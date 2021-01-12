import os
import secrets
from flask import render_template, url_for, flash, redirect, request, abort
from application import app, db, bcrypt
from application.forms.teacher import *
from application.models.general import *
from flask_login import login_user, current_user, logout_user, login_required


