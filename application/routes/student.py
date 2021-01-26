import os
import secrets
import json
from time import sleep
from requests import get, post
from flask import render_template, url_for, flash, redirect, request, abort, session
from application import app, db, bcrypt
from application.forms.student import *
from application.models.general import *
from flask_login import login_user, current_user, logout_user, login_required
from application.settingssecrets import JUDGE0_AUTHN_TOKEN


@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    form = StudentLoginForm()
    if form.validate_on_submit():
        student_identifier = form.code.data
        student = Student.query.filter_by(identifier=student_identifier).first()
        if student:
            session['student_id'] = form.code.data
            return redirect(url_for('student_submit_problem', class_identifier=request.args.get('class_identifier'),
                                    problem_identifier=request.args.get('problem_identifier')))
        print('lul')
    return render_template('student/general/login.html', form=form)


@app.route('/class/<string:class_identifier>/problem/<string:problem_identifier>/submit', methods=['GET', 'POST'])
def student_submit_problem(class_identifier, problem_identifier):
    if 'student_id' not in session:
        return redirect(
            url_for('student_login', class_identifier=class_identifier, problem_identifier=problem_identifier))

    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    problem = Problem.query.filter_by(identifier=problem_identifier, class_=class_).first_or_404()
    form = SubmitSolutionForm()
    form.language.choices = [(p.number, p.name) for p in problem.languages]
    if form.validate_on_submit():
        language = form.language.data
        file = form.file.data.read()
        if len(file) > 100000:
            form.file.errors.append('The maximum file size you can upload is 100 kilobytes.')
        print(language)

        body = {
            "submissions": [
                {
                    "language_id": language,
                    "source_code": file.decode("utf-8")
                }
            ]
        }

        print(str(file))

        token = json.loads(post('https://judge0-fhwnc7.vishnus.me/submissions/batch?base64_encoded=false', data=json.dumps(body),
                   headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN, 'Content-Type': 'application/json'}).text)[0]['token']


        sleep(4)

        print(get(
            f'https://judge0-fhwnc7.vishnus.me/submissions/batch?tokens={token}&base64_encoded=false&fields=token,stdout,stderr,status_id,language_id',
            headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN}).text)

    return render_template('student/general/submit.html', problem=problem, class_=class_, form=form)
