from application import app
from flask import render_template, abort
from flask_login import login_user, current_user, logout_user, login_required


@app.route('/login')
def login():
    return render_template('general/login.html', page_title='Login')
