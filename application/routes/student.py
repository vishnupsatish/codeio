import json
import boto3
from functools import wraps
from time import sleep
from requests import get, post
from flask import render_template, url_for, jsonify, flash, redirect, request, abort, session
from application import app, db, celery
from application.forms.student import *
from application.models.general import *
from application.utils import upload_submission_file, delete_submission_files
from application.settingssecrets import JUDGE0_AUTHN_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME

# Initialize AWS's Python SDK (Boto3) resource (higher-level API) with the access key and secret access key
s3 = boto3.resource('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# Initialize AWS's Python SDK (Boto3) client (lower-level API) with the access key and secret access key
s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name='ca-central-1')

# Set AWS bucket name
bucket_name = AWS_BUCKET_NAME


# Create a decorator function
def abort_student_not_found(f):
    # When this function is used as a decorator, the @wraps calls the decorator
    # function with the function below the decorator as the parameter "f", and any
    # arguments and keyword arguments are also passed in and can be passed to the
    # original function as well
    @wraps(f)
    def decorator(*args, **kwargs):
        # If the student is not logged in, then abort 404
        if 'student_id' not in session:
            abort(404)

        # If the student is logged in, then return the original function
        return f(*args, **kwargs)

    # If the function is used as a decorator, then return
    # the decorator function which will be called
    return decorator


# Create another decorator function
def login_student_not_found(f):
    # When this function is used as a decorator, the @wraps calls the decorator
    # function with the function below the decorator as the parameter "f", and any
    # arguments and keyword arguments are also passed in and can be passed to the
    # original function as well
    @wraps(f)
    # Get the class_identifier and problem_identifier which will be passed from the URL function
    def decorator(class_identifier, problem_identifier, *args, **kwargs):

        # If the student is not logged in, redirect them to the login page
        if 'student_id' not in session:
            flash('Please enter your student code and log in to submit.', 'info')
            return redirect(
                url_for('student_login', class_identifier=class_identifier, problem_identifier=problem_identifier))

        # If the class doesn't exist, abort with a 404 error code
        class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()

        # Get the student that is supposedly authorized to see the problem (is in the same class)
        student = Student.query.filter_by(identifier=session['student_id'], class_=class_).first()

        # If the student is not authorized to see the problem, then flash so and go to the student login
        if not student:
            del session['student_id']
            flash('You are not authorized to see the problem. Please enter your student code.', 'danger')
            return redirect(
                url_for('student_login', class_identifier=class_identifier, problem_identifier=problem_identifier))

        # If the student is logged in and authorized to see the problem, then return the original function
        return f(class_identifier, problem_identifier, *args, **kwargs)

    # If the function is used as a decorator, then return
    # the decorator function which will be called
    return decorator


# The student login route
@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    form = StudentLoginForm()

    # If the form was successfully submitted
    if form.validate_on_submit():

        # Get the student code that was entered
        student_identifier = form.code.data

        # Get the student's DB object
        student = Student.query.filter_by(identifier=student_identifier).first()

        # Get the class passed in from the URL parameter (the class identifier will ALWAYS be passed in)
        class_ = Class_.query.filter_by(identifier=request.args.get('class_identifier')).first()

        # If the student exists and the student is in the gievn class,
        # then redirect them to the problem they were trying to reach
        if student and student in class_.students:

            # Set the session object of student_id to the student's identifier (student code)
            session['student_id'] = form.code.data
            return redirect(url_for('student_submit_problem', class_identifier=request.args.get('class_identifier'),
                                    problem_identifier=request.args.get('problem_identifier')))
        # If the student was not found, then go back to the login page
        # and let them know there was an issue logging them in
        else:
            flash('Student not found. Please check your code and whether you are authorized to see the problem.',
                  'danger')
    return render_template('student/general/login.html', form=form, page_title=f'Student Login')


# Student log out
@app.route('/student-logout')
def student_logout():
    # If the student is already logged out, then tell them to close the tab
    if 'student_id' not in session:
        return "<p>You have been logged out. You may now close this tab</p>"

    # Delete the session object of student_id
    del session['student_id']
    return redirect(url_for('student_logout'))


# The page to submit a problem
@app.route('/student/class/<string:class_identifier>/problem/<string:problem_identifier>/submit',
           methods=['GET', 'POST'])
@login_student_not_found
def student_submit_problem(class_identifier, problem_identifier):
    # Get the DB objects of the current class, problem, student, and their submissions of this problem
    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    student = Student.query.filter_by(identifier=session['student_id'], class_=class_).first()
    problem = Problem.query.filter_by(identifier=problem_identifier, class_=class_).first_or_404()
    submissions = Submission.query.filter_by(problem=problem, student=student).all()

    # Check if the student can submit (if the problem allows
    # multiple submissions or the student has not submitted already)
    student_can_submit = (problem.allow_multiple_submissions or len(
        submissions) == 0) and problem.allow_more_submissions
    form = SubmitSolutionForm()

    # Set the language choices to the languages that were allowed by the teacher
    form.language.choices = [(p.number, p.name) for p in problem.languages]

    # If the form was submitted successfully
    if form.validate_on_submit():

        # Get the file
        file = form.file.data

        # Read the file's text
        file_data = file.read()

        # Go back to the beginning of the file, so if read is called again, the same text is returned
        file.seek(0)

        # If the problem is not to be auto graded
        if not problem.auto_grade:

            # Upload the submission file with the language, file, class, the s3
            # resource, bucket name, and associate the submission to the current student
            submission_file = upload_submission_file(form.language.data, file, class_, problem, s3,
                                                     bucket_name, student)

            # If there was an error submitting the file
            if type(submission_file) is not tuple:
                # Flash the string that was returned by the function, then
                # redirect back to the same page to avoid submit on reload
                flash(submission_file, 'danger')
                return redirect(url_for('student_submit_problem', class_identifier=class_identifier,
                                        problem_identifier=problem_identifier))

            # if the file was submitted successfully, get the submission object and the UUID
            submission_file, uuid = submission_file

            # Flash that the file was submitted successfully, assign the
            # highest marks, then redirect back to the same page
            flash('Your file has been submitted successfully.', 'success')
            submission_file.marks = problem.total_marks
            db.session.commit()
            return redirect(url_for('student_submit_problem', class_identifier=class_identifier,
                                    problem_identifier=problem_identifier))

        # If the problem is to be auto graded
        submission_file = upload_submission_file(form.language.data, file, class_, problem, s3,
                                                 bucket_name, student)

        # If there was an error submitting the file
        if type(submission_file) is not tuple:
            # Flash the string that was returned by the function, then
            # redirect back to the same page to avoid submit on reload
            flash(submission_file, 'danger')
            return redirect(url_for('student_submit_problem', class_identifier=class_identifier,
                                    problem_identifier=problem_identifier))

        # if the file was submitted successfully, get the submission object and the UUID
        submission_file, uuid = submission_file

        # Call the Celery task to judge the code, then return the result
        task = student_judge_code.delay(form.language.data, file_data.decode('utf-8'), problem.id, student.id,
                                        submission_file.id)

        # Set the submission's UUID to the Celery task's ID
        submission_file.uuid = task.id
        db.session.commit()

        # Redirect to the student's submission page
        return redirect(url_for('student_submission', task_id=task.id))

    return render_template('student/general/submit.html', problem=problem, class_=class_, form=form,
                           student_can_submit=student_can_submit, submissions=submissions, student=student,
                           page_title=f'Submit to {problem.title}')


# The Celery task to judge the code; bind=True passes the self
# parameter automatically and allows it to update its own state
@celery.task(bind=True)
def student_judge_code(self, language, file, problem, student, submission):
    # Get the problem, student, and submission
    problem = Problem.query.filter_by(id=problem).first()
    student = Student.query.filter_by(id=student).first()
    submission = Submission.query.filter_by(id=submission).first()

    # Create the body to be sent to the Judge0 API through a POST request
    body = {
        "submissions": [
        ]
    }

    # For every input file in the problem
    for i, _ in enumerate(problem.input_files):
        # Get the input and output file
        input_file = problem.input_files[i]
        output_file = problem.output_files[i]

        # Get the text from S3
        input_file_data = s3.Object(bucket_name, input_file.file_path).get()['Body'].read().decode('utf-8')
        output_file_data = s3.Object(bucket_name, output_file.file_path).get()['Body'].read().decode('utf-8')

        # Add the language, source code, the STDIN (standard input), expected output, time limit, and memory limit
        body['submissions'].append(
            {'language_id': int(language), 'source_code': file, 'stdin': input_file_data,
             'expected_output': output_file_data, 'cpu_time_limit': problem.time_limit,
             'memory_limit': problem.memory_limit * 1000})

    # Send the API request and get the tokens from Judge0
    judge0_tokens = json.loads(
        post('https://judge0-fhwnc7.vishnus.me/submissions/batch?base64_encoded=false', data=json.dumps(body),
             headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN, 'Content-Type': 'application/json'}).text)

    print(judge0_tokens)

    # Wait 2 seconds to allow execution to complete
    sleep(2)

    # Get a comma-separated string for each token
    tokens = ''

    if not judge0_tokens[0].get('token'):
        print("IDIOTBOX")
        return submission.id

    # For each token from the first to the second last, append the token as well as a comma
    for jt in judge0_tokens[:-1]:
        tokens += jt['token'] + ','

    # Append the last token with no comma
    tokens += judge0_tokens[-1]['token']

    # Continue calling the Judge0 API to get the results, until the results finally arrive
    while True:

        # Pass each token to get a batch of submission
        result = json.loads(get(
            f'https://judge0-fhwnc7.vishnus.me/submissions/batch?tokens={tokens}&base64_encoded=false&fields=token,stdout,stderr,language_id,time,memory,expected_output,compile_output,status',
            headers={'X-Auth-Token': JUDGE0_AUTHN_TOKEN}).text)

        # Since result is now a Python dict object, we can set the total
        # marks earned and total available marks in the dict itself
        result['total_marks_earned'] = 0
        result['total_marks'] = problem.total_marks

        # If the any of the submissions are still being processed (a status of 1: in queue. a status of 2: processing)
        if 1 in [s['status']['id'] for s in result['submissions']] or 2 in [s['status']['id'] for s in
                                                                            result['submissions']]:
            # Wait two seconds, then go into the while loop again
            sleep(2)
            continue

        # For each submission that was returned
        for i, s in enumerate(result['submissions']):
            # get the input and output files and the relevant info, such as the time, memory, standard errors, etc
            inp = problem.input_files[i]
            out = problem.output_files[i]
            time = s['time']
            memory = s['memory']
            stderr = s['stderr']
            stdout = s['stdout']
            token = s['token']
            compile_output = s['compile_output']
            expected_output = s['expected_output']

            # Get the relevant status DB object based on the status id that was returned
            status = Status.query.filter_by(number=s['status']['id']).first()

            # If the status id is 2 "Accepted", then set correct to True for that result
            correct = True if status.number == 3 else False

            # Get the total marks for that specific result, such that each result is weighted equally
            total_marks = round(problem.total_marks / len(problem.input_files), 2)

            # Get the marks earned
            marks = round(problem.total_marks / len(problem.input_files), 2) if correct else 0

            # Set the relevant fields to be returned, such as whether it was correct, the
            # name of the status, the marks earned, total marks, etc.
            result['submissions'][i]['correct'] = correct
            result['submissions'][i]['status'] = status.name
            result['submissions'][i]['total_marks'] = total_marks
            result['submissions'][i]['marks'] = marks
            result['total_marks_earned'] += marks

            # Delete the expected output field to the user cannot see it on the front-end
            del result['submissions'][i]['expected_output']

            # Create a new result and associate it to the input and output files, a status, etc
            r = Result(input_file=inp, output_file=out, submission=submission, token=token, stderr=stderr,
                       stdout=stdout,
                       memory=memory, compile_output=compile_output, time=time, expected_output=expected_output,
                       correct=correct, status=status, marks_out_of=total_marks, marks=marks)

            db.session.add(r)

        # Get the total marks earned from that submission
        submission.marks = round(result['total_marks_earned'], 2)

        # Send that as well
        result['total_marks_earned'] = submission.marks

        # Commit the changes
        db.session.commit()

        # Return the result and the submission's id
        return result, submission.id


# Get the status of a submission
@app.route('/status/<task_id>')
def task_status(task_id):
    # Get the result of the student_judge_code Celery task
    task = student_judge_code.AsyncResult(task_id)

    print(task.state)

    # If the task was successful and is finished
    if task.state == 'SUCCESS' and type(task.get()) != int:
        # Get the submission id and the result Python dict
        result, submission_id = task.get()

        # Get the submission DB object
        submission = Submission.query.filter_by(id=submission_id).first()

        # In the case the teacher changed the submission's marks
        # manually, then update that in the result Python dict
        result['total_marks_earned'] = submission.marks

        # Return the state of the task as well as the result, all converted to JSOn
        return jsonify({'state': task.state, 'result': result})

    elif (task.state == 'FAILURE' or type(task.get()) == int) and task.state != 'PENDING':
        # If there was an error in judging the code, then delete the submission
        try:
            submission = Submission.query.filter_by(id=task.get()).first()

            delete_submission_files(0, s3, bucket_name, files=[submission])

            db.session.delete(submission)

            db.session.commit()
        except:
            pass

        return jsonify({'state': 'ERROR',
                        'result': 'There was an unexpected error while attempting to submit your solution. Please try again. This submission will be deleted. You may now go back to the problem'})

    # Return the state of the task if it is not complete yet
    return jsonify({'state': 'PENDING'})


# View the results of a specific submission
@app.route('/student/submission/<task_id>')
@abort_student_not_found
def student_submission(task_id):
    # Get the student, submission, and problem from the database
    student = Student.query.filter_by(identifier=session['student_id']).first()
    submission = Submission.query.filter_by(uuid=task_id, student=student).first_or_404()
    problem = submission.problem

    # Generate the presigned URL for the code
    presigned_url = s3_client.generate_presigned_url('get_object',
                                                     Params={'Bucket': bucket_name, 'Key': submission.file_path},
                                                     ExpiresIn=3600)

    # Show a different HTML page whether or not the submission was to be auto-graded
    if not problem.auto_grade:
        return render_template('student/general/submission-plain.html', submission=submission,
                               presigned_url=presigned_url, page_title=f'Submission to {problem.title}')

    return render_template('student/general/submission.html', task_id=task_id, submission=submission,
                           time=problem.time_limit, presigned_url=presigned_url,
                           page_title=f'Submission to {problem.title}')
