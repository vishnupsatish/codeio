import os
import secrets
import json
import boto3
from time import sleep
from requests import get, post
from flask import render_template, url_for, jsonify, flash, redirect, request, abort, session
from application import app, db, bcrypt, celery
from application.forms.student import *
from application.models.general import *
from application.utils import upload_submission_file
from flask_login import login_user, current_user, logout_user, login_required
from application.settingssecrets import JUDGE0_AUTHN_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

s3 = boto3.resource('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name='ca-central-1')

bucket_name = 'code-execution-grade-10'


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
        else:
            flash('Student not found. Please check your code.', 'danger')
    return render_template('student/general/login.html', form=form)


@app.route('/student-logout')
def student_logout():
    del session['student_id']
    return "<p>You have been logged out. You may now close this tab</p>"


@app.route('/student/class/<string:class_identifier>/problem/<string:problem_identifier>/submit', methods=['GET', 'POST'])
def student_submit_problem(class_identifier, problem_identifier):
    if 'student_id' not in session:
        return redirect(
            url_for('student_login', class_identifier=class_identifier, problem_identifier=problem_identifier))

    student = Student.query.filter_by(identifier=session['student_id']).first()
    if not student:
        del session['student_id']
        return redirect(
            url_for('student_login', class_identifier=class_identifier, problem_identifier=problem_identifier))

    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    problem = Problem.query.filter_by(identifier=problem_identifier, class_=class_).first_or_404()
    submissions = Submission.query.filter_by(problem=problem, student=student).all()
    student_can_submit = problem.allow_multiple_submissions or len(submissions) == 0
    form = SubmitSolutionForm()
    form.language.choices = [(p.number, p.name) for p in problem.languages]

    if form.validate_on_submit():
        file = form.file.data

        file_data = file.read()

        file.seek(0)

        if not problem.auto_grade:
            submission_file, uuid = upload_submission_file(form.language.data, file, class_, problem, s3,
                                                           bucket_name, student)
            if type(submission_file) is not Submission:
                flash(submission_file, 'danger')
                return redirect(url_for('student_submit_problem', class_identifier=class_identifier,
                                        problem_identifier=problem_identifier))

            flash('Your file has been submitted successfully.', 'success')
            return redirect(url_for('student_submit_problem', class_identifier=class_identifier,
                                    problem_identifier=problem_identifier))

        submission_file, uuid = upload_submission_file(form.language.data, file, class_, problem, s3,
                                                       bucket_name, student)
        if type(submission_file) is not Submission:
            flash(submission_file, 'danger')
            return redirect(url_for('student_submit_problem', class_identifier=class_identifier,
                                    problem_identifier=problem_identifier))

        task = student_judge_code.delay(form.language.data, file_data.decode('utf-8'), problem.id, student.id,
                                        submission_file.id)
        submission_file.uuid = task.id
        db.session.commit()

        return redirect(url_for('student_submission', task_id=task.id))

    return render_template('student/general/submit.html', problem=problem, class_=class_, form=form,
                           student_can_submit=student_can_submit, submissions=submissions, student=student)


@celery.task(bind=True)
def student_judge_code(self, language, file, problem, student, submission):
    problem = Problem.query.filter_by(id=problem).first()
    student = Student.query.filter_by(id=student).first()
    submission = Submission.query.filter_by(id=submission).first()

    body = {
        "submissions": [
        ]
    }

    for i, _ in enumerate(problem.input_files):
        input_file = problem.input_files[i]
        output_file = problem.output_files[i]
        input_file_data = s3.Object(bucket_name, input_file.file_path).get()['Body'].read().decode('utf-8')
        output_file_data = s3.Object(bucket_name, output_file.file_path).get()['Body'].read().decode('utf-8')

        body['submissions'].append(
            {'language_id': int(language), 'source_code': file, 'stdin': input_file_data,
             'expected_output': output_file_data, 'cpu_time_limit': problem.time_limit,
             'memory_limit': problem.memory_limit * 1000})

    judge0_tokens = json.loads(
        post('https://judge0-fhwnc7.vishnus.me/submissions/batch?base64_encoded=false', data=json.dumps(body),
             headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN, 'Content-Type': 'application/json'}).text)

    print(judge0_tokens)

    sleep(problem.time_limit + 2)

    tokens = ''

    for jt in judge0_tokens[:-1]:
        tokens += jt['token'] + ','

    tokens += judge0_tokens[-1]['token']

    result = json.loads(get(
        f'https://judge0-fhwnc7.vishnus.me/submissions/batch?tokens={tokens}&base64_encoded=false&fields=token,stdout,stderr,language_id,time,memory,expected_output,compile_output,status',
        headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN}).text)

    print(result)

    result['total_marks_earned'] = 0
    result['total_marks'] = problem.total_marks

    for i, s in enumerate(result['submissions']):
        inp = problem.input_files[i]
        out = problem.output_files[i]
        time = s['time']
        memory = s['memory']
        stderr = s['stderr']
        stdout = s['stdout']
        token = s['token']
        compile_output = s['compile_output']
        expected_output = s['expected_output']
        status = Status.query.filter_by(number=s['status']['id']).first()
        correct = True if status.number == 3 else False
        total_marks = problem.total_marks / len(problem.input_files)
        marks = problem.total_marks / len(problem.input_files) if correct else 0
        result['submissions'][i]['correct'] = correct
        result['submissions'][i]['status'] = status.name
        result['submissions'][i]['total_marks'] = total_marks
        result['submissions'][i]['marks'] = marks
        result['total_marks_earned'] += marks
        del result['submissions'][i]['expected_output']
        r = Result(input_file=inp, output_file=out, submission=submission, token=token, stderr=stderr, stdout=stdout,
                   memory=memory, compile_output=compile_output, time=time, expected_output=expected_output,
                   correct=correct, status=status, marks_out_of=total_marks, marks=marks)

        db.session.add(r)

    submission.marks = result['total_marks_earned']

    db.session.commit()

    self.state = 'SUCCESS'

    return result


@app.route('/status/<task_id>')
def task_status(task_id):
    task = student_judge_code.AsyncResult(task_id)
    print(task.state)

    if task.state == 'SUCCESS':
        result = task.get()
        return jsonify({'state': task.state, 'result': result})

    return jsonify({'state': task.state})


@app.route('/student/submission/<task_id>')
def student_submission(task_id):
    if 'student_id' not in session:
        return abort(404)

    submission = Submission.query.filter_by(uuid=task_id).first_or_404()
    problem = submission.problem

    print(problem.auto_grade)
    presigned_url = s3_client.generate_presigned_url('get_object',
                                                     Params={'Bucket': bucket_name, 'Key': submission.file_path},
                                                     ExpiresIn=3600)
    if not problem.auto_grade:
        return render_template('student/general/submission-plain.html', submission=submission,
                               presigned_url=presigned_url)

    return render_template('student/general/submission.html', task_id=task_id, submission=submission,
                           time=problem.time_limit, presigned_url=presigned_url)
