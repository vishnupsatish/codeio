import os
import time
import boto3
import mistune
import mosspy
import random
import string
from hashlib import sha256
from secrets import token_urlsafe
from functools import wraps
from cryptography.fernet import Fernet
from flask import render_template, url_for, flash, redirect, request, abort, send_file, jsonify
from application import app, db, bcrypt, mail, serializer, celery, limiter
from flask_login import login_user, current_user, logout_user, login_required
from application.forms.teacher import *
from application.settingssecrets import *
from application.models.general import *
from application.utils import *

# Initialize AWS's Python SDK (Boto3) resource (higher-level API) with the access key and secret access key
s3 = boto3.resource('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# Initialize AWS's Python SDK (Boto3) client (lower-level API) with the access key and secret access key
s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name='ca-central-1')

# Set AWS bucket name
bucket_name = AWS_BUCKET_NAME

# Initialize Fernet encryption (for encryption of MOSS codes)
fernet = Fernet(os.environ.get('FERNET_KEY').encode())


# Create a decorator function
def abort_teacher_not_confirmed(f):
    # When this function is used as a decorator, the @wraps calls the decorator
    # function with the function below the decorator as the parameter "f", and any
    # arguments and keyword arguments are also passed in and can be passed to the
    # original function as well
    @wraps(f)
    def decorator(*args, **kwargs):
        if not current_user.confirm:
            return redirect(url_for('teacher_confirm_account'))

        return f(*args, **kwargs)

    # If the function is used as a decorator, then return
    # the decorator function which will be called
    return decorator


# Route the favicon to the favicon image in the static directory
@app.route('/favicon.ico')
def favicon():
    return send_file('static/img/CodeIOFavicon.ico', mimetype='image/vnd.microsoft.icon')


@app.context_processor
def send_sha_function():
    return {'sha256': sha256, 'serializer': serializer}


# If the user goes to "/", redirect to the dashboard
@app.route('/')
def teacher_redirect_to_dashboard():
    if not current_user.is_authenticated:
        return render_template('general/index.html',
                               page_title='CodeIO - Assess coding skills through interactive problems')

    return redirect(url_for('teacher_login'))


# About CodeIO page
@app.route('/about')
def about():
    if not current_user.is_authenticated:
        return redirect(url_for('teacher_redirect_to_dashboard'))
    return render_template('general/index.html',
                           page_title='CodeIO - Assess coding skills through interactive problems')


# Log the user out
@app.route('/logout')
def logout():
    # If the user is not logged in or have not confirmed their email, don't log them out
    if not current_user.is_authenticated:
        abort(404)

    if not current_user.confirm:
        abort(404)

    logout_user()
    return redirect(url_for('teacher_login'))


# Registration page
@app.route('/teacher-register', methods=['GET', 'POST'])
def teacher_register():
    # If the user is already logged in, redirect to the dashboard
    if current_user.is_authenticated:
        return redirect(url_for('teacher_dashboard'))

    # Create form using Flask-WTF
    form = RegistrationForm()

    # If form was submitted successfully, create a user and redirect to confirm account page
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')
        user = User(name=form.name.data, email=form.email.data,
                    password=hashed_password)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        token = serializer.dumps(current_user.email, salt=os.environ.get('SECRET_KEY'))

        # Resend confirmation email, if there was an error, say so
        try:
            mail.send_message(sender='contact@codeio.tech',
                              subject='Your CodeIO Confirmation Email',
                              body=f'Click on the below link to confirm your CodeIO account\n{url_for("teacher_token", token=token, _external=True)}',
                              recipients=[current_user.email])
        except:
            flash('There was an error sending a confirmation email.', 'danger')

        return redirect(url_for('teacher_login'))

    return render_template('teacher/general/register.html', form=form, page_title='Register')


# Login page
@app.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
    # If the user is already logged in, redirect to the dashboard
    if current_user.is_authenticated:
        return redirect(url_for('teacher_dashboard'))

    # Create form using Flask-WTF
    form = LoginForm()

    # If the form has been successfully submitted
    if form.validate_on_submit():

        # Check if the user exists and whether the bcrypt hash of the input and the user's hash match
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):

            # Log the user in and redirect to the dashboard if there is not "?next=" parameter in the URL
            login_user(user, remember=form.remember.data)
            return redirect(url_for('teacher_dashboard')) if not request.args.get('next') else redirect(
                request.args.get('next'))

        # Flash that the login was unsuccessful (Flash is an in-built
        # Flask tool that sends messages which can be retrieved on the HTML page)
        else:
            flash('Login Unsuccessful. Please check your email and password', 'danger')
    return render_template('teacher/general/login.html', form=form, page_title='Login')


# A route to send a password reset email in case the user forgets their password
@app.route('/forgot-password', methods=['GET', 'POST'])
def teacher_forgot_password():
    # If the user is logged in, abort with 404 code
    if current_user.is_authenticated:
        abort(404)

    form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = serializer.dumps(user.email, salt=os.environ.get('SECRET_KEY') + 'reset')
            mail.send_message(sender='contact@codeio.tech',
                              subject='Reset your password on CodeIO',
                              body=f'Click on the below link to reset your password\n{url_for("teacher_forgot_password_token", token=token, _external=True)}',
                              recipients=[user.email])
        time.sleep(1)
        flash('An email has been sent to reset your password if the user exists.', 'info')
        return redirect(url_for('teacher_forgot_password'))

    return render_template('teacher/general/forgot-password.html', form=form, page_title='Forgot password')


# A route to change a user's password based on the token that was sent to their email
@app.route('/forgot-password/<token>', methods=['GET', 'POST'])
def teacher_forgot_password_token(token):
    # If the user is logged in, abort with 404 code
    if current_user.is_authenticated:
        abort(404)

    # Get the user's email based on the serializer's value
    try:
        user = User.query.filter_by(
            email=serializer.loads(token, salt=os.environ.get('SECRET_KEY') + 'reset', max_age=7200)).first()
    # If there was an issue, that means the token was incorrect, then abort with 404
    except:
        abort(404)

    # Initialize the form
    form = ChangePasswordForm()

    # If the form validated, then generate a password hash,
    # change the user's password, then let the user know
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been changed.', 'success')
        return redirect(url_for('teacher_login'))

    # Show the HTML page
    return render_template('teacher/general/change-password.html', form=form, page_title='Change your password')


# A route to confirm the user's account
@app.route('/confirm-account', methods=['GET', 'POST'])
def teacher_confirm_account():
    # If the user is not logged in or the user has already confirmed, then return
    if not current_user.is_authenticated:
        abort(404)

    if current_user.confirm:
        return redirect(url_for('teacher_dashboard'))

    # Create the form which allows resending confirmation emails
    form = ConfirmAccountForm()

    # If the form was validated, generate a timed token, then send the message and let the user know
    if form.validate_on_submit():
        token = serializer.dumps(current_user.email, salt=os.environ.get('SECRET_KEY'))

        # Resend confirmation email, if there was an error, say so
        try:
            mail.send_message(sender='contact@codeio.tech',
                              subject='Your CodeIO Confirmation Email',
                              body=f'Click on the below link to confirm your CodeIO account\n{url_for("teacher_token", token=token, _external=True)}',
                              recipients=[current_user.email])
        except:
            flash('There was an error sending a confirmation email.', 'danger')
            return redirect(url_for('teacher_confirm_account'))

        flash('The email has been sent to you.', 'success')

        return redirect(url_for('teacher_confirm_account'))

    return render_template('teacher/general/confirm-account.html', form=form, page_title='Confirm Account')


# Route to check a user's token
@app.route('/token/<token>')
def teacher_token(token):
    # If the user has already confirmed, abort with
    # 404, then if the user is logged in, log them out
    if current_user.is_authenticated:
        if current_user.confirm:
            abort(404)
        logout_user()

    # Load the token, then check if the emails match and set that the user has confirmed
    try:
        email = serializer.loads(token, salt=os.environ.get('SECRET_KEY'), max_age=7200)

        # Get the user from the token
        user = User.query.filter_by(email=email).first_or_404()

        # Log the user in
        login_user(user)

        # If the user has confirmed, abort with 404
        if user.confirm:
            abort(404)

        # Set the user's confirm attribute to True, then commit
        current_user.confirm = True
        db.session.commit()

        # Let the user know they have been confirmed
        flash('Your email has been confirmed.', 'success')
        return redirect(url_for('teacher_dashboard'))

    # If there was an error while loading the token, return so
    except:
        return render_template('errors/token_expired.html'), 403

    abort(404)


# Delete a user's account
@app.route('/delete-account/')
def teacher_delete_account():
    if not current_user.is_authenticated:
        abort(404)

    # Hash the same properties as was passed from the class page
    sha_hash_contents = sha256(
        f'{current_user.id}{current_user.email}{current_user.password}'.encode('utf-8')).hexdigest()

    # if the hashes don't match, don't delete the account
    if sha_hash_contents != request.args.get('hash'):
        return render_template('errors/token_expired.html'), 403

    # Get the user and delete the account
    user = User.query.filter_by(id=current_user.id).first()

    logout_user()

    db.session.delete(user)
    db.session.commit()

    flash('Your account has been deleted.', 'success')

    return redirect(url_for('teacher_register'))


# A route to update the current user's account
@app.route('/account', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_account():
    form = UpdateAccountForm()

    # If the form was submitted successfully,
    # change the user's attributes and commit
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.moss_id = fernet.encrypt(form.moss_code.data.encode()).decode()
        db.session.commit()
        flash('Your account has been updated.', 'success')
        return redirect(url_for('teacher_account'))

    # Set the default form values to the user's attributes
    form.name.data = current_user.name

    if current_user.moss_id:
        form.moss_code.data = fernet.decrypt(current_user.moss_id.encode()).decode()

    return render_template('teacher/general/account.html', form=form, page_title='Your account')


# The teacher's dashboard
@app.route('/dashboard')
@login_required
@abort_teacher_not_confirmed
def teacher_dashboard():
    # Get all of the classes that are associated to the current user
    # classes_ = Class_.query.filter_by(user=current_user).all()
    classes_ = current_user.classes
    return render_template('teacher/general/dashboard.html', classes_=classes_, page_title='Dashboard')


# Creating a new class
@app.route('/new-class', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def new_class():
    # Initialize the NewClassForm from Flask-WTF
    form = NewClassForm()
    if form.validate_on_submit():
        # If the form was successfully submitted, create a new class and Flash the result to the user
        class_ = Class_(name=form.name.data, description=form.description.data,
                        identifier=token_urlsafe(16))
        class_.users.append(current_user)
        db.session.add(class_)
        db.session.commit()
        flash('The class has been created successfully.', 'success')
        return redirect(url_for('teacher_dashboard'))
    return render_template('teacher/general/new-class.html', form=form, page_title='New Class')


# A class's homepage
@app.route('/class/<string:identifier>/home')
@login_required
@abort_teacher_not_confirmed
def teacher_class_home(identifier):
    # Query the class from it's unique identifier, and if the class doesn't exist, abort with 404
    class_ = Class_.query.filter_by(identifier=identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    # Get all of the problems associated to that class
    problems = Problem.query.filter_by(class_=class_).order_by(Problem.create_date_time.desc()).all()

    # Call a utility function which, for each problem, gets the
    # number of unique students that have submitted the problem
    u = get_unique_students_problem(problems)
    return render_template('teacher/classes/home.html', problems=problems, class_=class_, identifier=identifier, u=u,
                           page_title=class_.name)


# A route for deleting a class (uses hashing to ensure the user themselves requested the deletion
@app.route('/class/<string:identifier>/delete')
def teacher_class_delete(identifier):
    # If the user isn't logged in, don't tell them that this page exists!
    if not current_user.is_authenticated:
        abort(404)

    # Query the class from it's unique identifier, and if the class doesn't exist, abort with 404
    class_ = Class_.query.filter_by(identifier=identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    # Hash the same properties as was passed from the class page
    sha_hash_contents = sha256(
        f'{class_.identifier}{class_.id}{current_user.password}'.encode('utf-8')).hexdigest()

    # if the two hashes are not the same, then abort with a 404 exit code
    if sha_hash_contents != request.args.get('hash'):
        return render_template('errors/token_expired.html'), 403

    # For every problem, delete the associated input files, output files, and submissions
    for problem in class_.problems:
        delete_submission_files(problem, s3, bucket_name)
        delete_input_output_files(problem, s3, bucket_name)

        # Delete the problem
        db.session.delete(problem)

        db.session.commit()

    class_.users = []

    # Delete the entire class along with any students (due to the all, delete cascade behaviour)
    db.session.delete(class_)

    db.session.commit()

    flash('The class has been deleted.', 'success')

    return redirect(url_for('teacher_dashboard'))


# The students from a particular class
@app.route('/class/<string:identifier>/users', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_class_students(identifier):
    # Get the class from the identifier in the URL
    class_ = Class_.query.filter_by(identifier=identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    # Initialize the NewStudentForm
    form = NewStudentForm()

    # If the form was submitted successfully, create a new student based on the
    # game, and generate a random alphanumeric code that the student will use to log in
    if form.validate_on_submit():
        student = Student(name=form.name.data, identifier=''.join(
            random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=8)), class_=class_)
        db.session.add(student)
        db.session.commit()
        flash('The student has been created successfully.', 'success')
        return redirect(url_for('teacher_class_students', identifier=identifier))

    # Get all of the students associated to that class
    students = class_.students

    marks = {}

    # For each student, get their mark for each problem based
    # on their highest submission by calling the utility function
    for student in students:
        marks[student] = get_student_mark(student, class_)

    key = serializer.dumps(class_.id, salt=os.environ.get('SECRET_KEY'))

    return render_template('teacher/classes/users.html', identifier=identifier, form=form, class_=class_,
                           students=students, marks=marks,
                           page_title=f'Students - {class_.name}', key=key)


# Options route
@app.route('/class/<string:identifier>/options', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_class_options(identifier):
    # Get the class from the identifier in the URL
    class_ = Class_.query.filter_by(identifier=identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    # Create two forms
    form = UpdateClassForm()

    form2 = LeaveClassForm()

    # Check if the update class form was submitted
    if form.update.data and form.validate_on_submit():
        # Update the class and let the student know
        class_.name = form.name.data
        class_.description = form.description.data
        db.session.commit()

        flash('Your changes have been made.', 'success')

        return redirect(url_for('teacher_class_options', identifier=identifier))

    # If the teacher has requested to leave the class
    if form2.submit.data and form2.validate_on_submit():
        # Remove them from the class, then let them know that they were removed
        class_.users.remove(current_user)
        db.session.commit()

        flash('You have successfully left the class.', 'success')

        return redirect(url_for('teacher_dashboard'))

    # Set the update class form's default values to
    # the class's values that exist in the database
    form.name.data = class_.name
    form.description.data = class_.description

    return render_template('teacher/classes/settings.html', class_=class_,
                           page_title=f'Options - {class_.name}', form1=form, form2=form2)


# Route to accept invite for a class
@app.route('/class/<string:identifier>/invite', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_class_invite(identifier):
    class_ = Class_.query.filter_by(identifier=identifier).first_or_404()

    # If the user is already in the class, abort with a 404
    if class_ in current_user.classes:
        abort(404)

    # If the serializer's result is incorrect, then let the user know and abort with a 403
    try:
        serial_encrypt = serializer.loads(request.args.get('key'), salt=os.environ.get('SECRET_KEY'), max_age=7200)
    except:
        return render_template('errors/token_expired.html', page_title='Token expired'), 403

    # If the user is requesting to the join the incorrect class, let the user know and abort with a 404
    if serial_encrypt != class_.id:
        return render_template('errors/token_expired.html', page_title='Token expired'), 403

    # If the user presses the button the confirm the addition
    # to the class, add them then redirect to the class
    form1 = ConfirmAdditionToClassForm()

    if form1.submit.data and form1.validate_on_submit():
        class_.users.append(current_user)
        db.session.commit()
        flash('You have been added to the class!', 'success')
        return redirect(url_for('teacher_class_home', identifier=class_.identifier))

    return render_template('teacher/classes/confirm-added-to-class.html', class_=class_, form=form1,
                           page_title='Join Class')


# Creating a new problem
@app.route('/class/<string:identifier>/new-problem', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_class_new_problem(identifier):
    class_ = Class_.query.filter_by(identifier=identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    form = NewProblemForm()

    # Set the language choices to what is returned by the
    # below utility function; this is done since languages
    # keep getting updated and I don't want to manually change it every time
    form.languages.choices = get_languages_form()

    # If the new problem form was successfully submitted
    if form.validate_on_submit():

        # Get each field, such as title, description, etc.
        title = form.title.data

        description = form.description.data

        # Convert the markdown description to HTML to store in the database
        description_html = mistune.html(description)

        time_limit = form.time_limit.data

        memory_limit = form.memory_limit.data

        marks_out_of = form.total_marks.data

        languages = form.languages.data

        allow_multiple_submissions = form.allow_multiple_submissions.data
        auto_grade = form.auto_grade.data
        visible = form.visible.data

        # Get each input and output file
        input1file = form.input1file.data
        input2file = form.input2file.data
        input3file = form.input3file.data
        input4file = form.input4file.data
        input5file = form.input5file.data

        output1file = form.output1file.data
        output2file = form.output2file.data
        output3file = form.output3file.data
        output4file = form.output4file.data
        output5file = form.output5file.data

        # Create a new problem with the attributes provided by the form
        problem = Problem(user=current_user, title=title, description=description, total_marks=marks_out_of,
                          allow_multiple_submissions=allow_multiple_submissions, auto_grade=auto_grade,
                          identifier=token_urlsafe(8), class_=class_, description_html=description_html, visible=visible)

        # If the user and entered the time limit/memory limit, add that as
        # well else keep it to the default as in the database
        if time_limit:
            problem.time_limit = time_limit
        if memory_limit:
            problem.memory_limit = memory_limit

        # For every language that the user chose, get the corresponding database
        # object then create a relationship between that problem and language
        for lang in languages:
            lang_object = Language.query.filter_by(number=int(lang)).first()
            problem.languages.append(lang_object)

        # If the user selects the "auto grade" checkbox
        if auto_grade:

            # Call the function 5 times to upload each input
            # and output file, the function returns text to flash
            # if the file size is too large else it returns none
            inout1 = upload_input_output_file(1, input1file, output1file, class_, problem, s3, bucket_name)
            if inout1 is not None:
                flash(inout1, 'danger')
            inout2 = upload_input_output_file(2, input2file, output2file, class_, problem, s3, bucket_name)
            if inout2 is not None:
                flash(inout2, 'danger')
            inout3 = upload_input_output_file(3, input3file, output3file, class_, problem, s3, bucket_name)
            if inout3 is not None:
                flash(inout3, 'danger')
            inout4 = upload_input_output_file(4, input4file, output4file, class_, problem, s3, bucket_name)
            if inout4 is not None:
                flash(inout4, 'danger')
            inout5 = upload_input_output_file(5, input5file, output5file, class_, problem, s3, bucket_name)
            if inout5 is not None:
                flash(inout5, 'danger')

        # Commit the changes to the database and let the user know the problem was created without problem!
        db.session.commit()
        flash('The problem has been created successfully.', 'success')
        return redirect(
            url_for('teacher_class_problem', class_identifier=identifier, problem_identifier=problem.identifier))

    return render_template('teacher/classes/new-problem.html', form=form, identifier=identifier, class_=class_,
                           page_title=f'New Problem - {class_.name}')


# Each problem's page
@app.route('/class/<string:class_identifier>/problem/<string:problem_identifier>', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_class_problem(class_identifier, problem_identifier):
    # Get the class the problem from the database based on each identifier as passed in from the URL
    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    problem = Problem.query.filter_by(identifier=problem_identifier, user=current_user, class_=class_).first_or_404()

    # Create two lists belonging to the presigned URLs from the input and output,
    # since every file is not publicly accessible (since students can then view the
    # input/output) and requires pre-signing using AWS's Boto3 SDK to be available for view to the teachers
    input_presigned_urls = []
    output_presigned_urls = []

    # For every input file, generate a presigned URL that expires in 1 hour
    for input_file in problem.input_files:
        input_presigned_urls.append(
            s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': input_file.file_path},
                                             ExpiresIn=3600))

    # For every output file, generate a presigned URL that expires in 1 hou
    for output_file in problem.output_files:
        output_presigned_urls.append(
            s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': output_file.file_path},
                                             ExpiresIn=3600))

    student_submissions = {}

    # For every student in the class:
    for student in class_.students:

        # Set that student's submissions to a list
        student_submissions[student] = []

        # Take the intersection (common elements) from that student's submissions as well
        # as that problem's submissions and sort the student's submissions based on the date
        # and time the submission was sent in descending order
        for submission in sorted(list(set(problem.submissions) & set(student.submissions)), key=lambda x: x.date_time,
                                 reverse=True):
            student_submissions[student].append(submission)

    # Since there are two tabs, problem info and student submissions, show the problem info as default
    show_student_submissions = 'dontshow'
    show_problem_info = ''

    # The is-active class identifier on the tab makes it blue and "selected"
    active_student_submissions = ''
    active_show_problem = 'is-active'

    # If the query parameter "show_student_submissions" is set to true, then show that tab and hide the problem info tab
    if request.args.get('show_student_submissions'):
        # The is-active class identifier on the tab makes it blue and "selected"
        active_student_submissions = 'is-active'
        active_show_problem = ''
        show_student_submissions = ''
        show_problem_info = 'dontshow'

    # The form to check a problem's submissions for plagiarism
    plagiarism_form = CheckPlagiarismForm()

    # If the form was successfully validated
    if plagiarism_form.validate_on_submit():
        # Call the Celery task to check for plagiarism
        task = teacher_check_for_plagiarism.delay(class_identifier=class_identifier,
                                                  problem_identifier=problem_identifier,
                                                  user_id=current_user.id)
        # Redirect to the plagiarism viewer page
        return redirect(url_for('teacher_class_problem_plagiarism', class_identifier=class_identifier,
                                problem_identifier=problem_identifier, task_id=task.id))

    return render_template('teacher/classes/problem.html', problem=problem, identifier=class_identifier,
                           input_presigned_urls=input_presigned_urls, output_presigned_urls=output_presigned_urls,
                           class_=class_, student_submissions=student_submissions,
                           active_student_submissions=active_student_submissions,
                           show_student_submissions=show_student_submissions, show_problem_info=show_problem_info,
                           active_show_problem=active_show_problem, page_title=f'{problem.title} - {class_.name}',
                           form=plagiarism_form)


# The page to show the MOSS links for each language in the problem
@app.route('/class/<string:class_identifier>/problem/<string:problem_identifier>/plagiarism-check/<string:task_id>')
def teacher_class_problem_plagiarism(class_identifier, problem_identifier, task_id):
    # Get the class and problem
    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    problem = Problem.query.filter_by(identifier=problem_identifier).first_or_404()

    flash(
        'If you leave this page, the plagiarism task link will not be shown to you again. Either save the MOSS link(s) or start another plagiarism check.',
        'warning')

    return render_template('teacher/classes/plagiarism-check.html', task_id=task_id, class_=class_, problem=problem,
                           page_title='Plagiarism check')


# The background task to return MOSS links for checking plagiarism
@celery.task(bind=True)
def teacher_check_for_plagiarism(self, class_identifier, problem_identifier, user_id):
    # Get the problem and the teacher that initiated the MOSS request
    problem = Problem.query.filter_by(identifier=problem_identifier).first()
    user = User.query.filter_by(id=user_id).first()

    languages = {}
    urls = {}

    if not user.moss_id:
        return 'Your MOSS user ID seems to be incorrect. Please update it.'

    # For every MOSS-compatible language, add its MOSSpy name to the languages dictionary
    for lang in problem.languages:
        if lang.short_name:
            languages[lang.short_name] = []

    # For every submission in the problem
    for submission in problem.submissions:
        # If the submission was done in a compatible language, add
        # it to the languages dictionary with the key being the MOSSpy name
        if submission.language.short_name in languages:
            languages[submission.language.short_name].append(submission)

    # For every MOSSpy compatible language
    for lang in languages:
        # Initialize the MOSSpy object
        moss = mosspy.Moss(fernet.decrypt(user.moss_id.encode()).decode(), lang)

        # For every submission
        for submission in languages[lang]:
            # Get the code from S3
            code_text = s3.Object(bucket_name, submission.file_path).get()['Body'].read().decode('utf-8')

            # Get the file name
            file_name = submission.file_path.split('/')[-1]

            # Create a temporary file on the system, then add that to the MOSSpy
            # initialization (since MOSSpy cannot read from Internet URLS)
            temp_file_path = f'application/temp/{file_name}'
            with open(temp_file_path, 'w') as file:
                file.write(code_text)
            moss.addFile(temp_file_path)

        # If there are submissions associated to the MOSSpy-compatible language
        if languages[lang]:

            # Try to send the files to MOSS, and if the connection was
            # reset, then we know that the MOSS ID of the user is incorrect
            try:
                urls[lang] = moss.send()

                # If the links are empty, delete the files then return
                if not urls[lang]:
                    for submission in languages[lang]:
                        file_name = submission.file_path.split('/')[-1]
                        temp_file_path = f'application/temp/{file_name}'
                        os.remove(temp_file_path)
                    return 'Your MOSS user ID seems to be incorrect. Please update it.'

            # If there was en error getting the links, delete the files then return
            except:
                for submission in languages[lang]:
                    file_name = submission.file_path.split('/')[-1]
                    temp_file_path = f'application/temp/{file_name}'
                    os.remove(temp_file_path)
                return 'Your MOSS user ID seems to be incorrect. Please update it.'

            # Create the MOSSResult db object
            moss_result = MOSSResult(link=urls[lang], uuid=celery.current_task.request.id, problem=problem)

            # Get the languages that have the specific short name (for example,
            # Clang++ and multiple versions of GCC for C++ have the same short name)
            languages_db = Language.query.filter_by(short_name=lang).all()

            # Add the languages that are common between the languages in the
            # problem and the languages that are associated to that short_name
            # (for example, if Clang++ has a short_name of cc, but is not a choice
            # in the problem, then don't add it)
            moss_result.languages.extend(list(set(languages_db) & set(problem.languages)))
            db.session.add(moss_result)

        # Remove each temp file
        for submission in languages[lang]:
            file_name = submission.file_path.split('/')[-1]
            temp_file_path = f'application/temp/{file_name}'
            os.remove(temp_file_path)

    db.session.commit()

    # If there are URLs, then let the user know the following:
    if not urls:
        return 'There needs to be at least two submissions of the same language.'

    # Return each URL
    return urls


# Get the status of a plagiarism task
@app.route('/plagiarism-status/<task_id>')
def teacher_get_plagiarism_task_status(task_id):
    # Get the MOSS results associated to that task id
    moss_results = MOSSResult.query.filter_by(uuid=task_id).all()

    # If the db object exists, then add the proper languages name (such as
    # "C++ (GCC 7.8.0)" instead of "cc") to the urls dictionary as the key
    # then add the URL as the value
    if moss_results:
        urls = {}
        for moss_r in moss_results:
            urls[', '.join([lang.name for lang in moss_r.languages])] = moss_r.link

        return jsonify({'state': 'SUCCESS', 'urls': urls})

    # If there are no associated db objects, then get the result
    task = teacher_check_for_plagiarism.AsyncResult(task_id)

    # If the task was successful, return the urls (this is meant as a fallback
    # if the db method somehow fails, though this should never be invoked)
    if task.status == 'SUCCESS':
        urls = task.get()

        return jsonify({'state': 'SUCCESS', 'urls': urls})

    # Let the JS know that the state is still pending
    return jsonify({'state': 'PENDING'})


# Route to delete a problem
@app.route('/class/<string:class_identifier>/problem/<string:problem_identifier>/delete')
def teacher_class_problem_delete(class_identifier, problem_identifier):
    if not current_user.is_authenticated:
        abort(404)

    # Get the class and problem
    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    problem = Problem.query.filter_by(identifier=problem_identifier, user=current_user, class_=class_).first_or_404()

    # Hash the same properties as was passed from the problem page
    sha_hash_contents = sha256(
        f'{class_.identifier}{class_.id}{problem.identifier}{problem.id}{current_user.password}'.encode(
            'utf-8')).hexdigest()

    # if the two hashes are not the same, then abort with a 404 exit code
    if sha_hash_contents != request.args.get('hash'):
        return render_template('errors/token_expired.html', page_title='Token expired'), 403

    # Delete the input and output files, as well as the submission files
    delete_input_output_files(problem, s3, bucket_name)

    delete_submission_files(problem, s3, bucket_name)

    # Delete the problem itself
    db.session.delete(problem)

    db.session.commit()

    # Let the user know, then redirect to the dashboard
    flash('The problem has been deleted.', 'success')

    return redirect(url_for('teacher_class_home', identifier=class_.identifier))


# Edit a problem
@app.route('/class/<string:class_identifier>/problem/<string:problem_identifier>/edit', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_class_problem_edit(class_identifier, problem_identifier):
    # Get the class the problem from the database based on each identifier as passed in from the URL
    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    problem = Problem.query.filter_by(identifier=problem_identifier, user=current_user, class_=class_).first_or_404()
    form = EditProblemForm()

    # Set the language choices to what is returned by the
    # below utility function; this is done since languages
    # keep getting updated and I don't want to manually change it every time
    form.languages.choices = get_languages_form()

    # if the form validated with no errors, update each field
    if form.validate_on_submit():
        if form.memory_limit.data:
            problem.memory_limit = form.memory_limit.data
        if form.time_limit.data:
            problem.time_limit = form.time_limit.data
        problem.title = form.title.data
        problem.description = form.description.data
        problem.description_html = mistune.html(form.description.data)
        problem.total_marks = form.total_marks.data
        problem.time_limit = form.time_limit.data
        problem.visible = form.visible.data

        # Reset, then change the problem's languages
        problem.languages = []
        for lang in form.languages.data:
            lang_object = Language.query.filter_by(number=int(lang)).first()
            problem.languages.append(lang_object)

        problem.allow_multiple_submissions = form.allow_multiple_submissions.data
        problem.allow_more_submissions = form.allow_more_submissions.data

        # Commit the changes the database then flash
        db.session.commit()

        flash('The problem has been updated.', 'success')

        return redirect(url_for('teacher_class_problem', class_identifier=class_identifier,
                                problem_identifier=problem_identifier))

    # Set the values in the form to the problem's existing attributes
    form.languages.data = [l.number for l in problem.languages]
    form.title.data = problem.title
    form.memory_limit.data = problem.memory_limit
    form.time_limit.data = problem.time_limit
    form.total_marks.data = problem.total_marks
    form.description.data = problem.description
    form.allow_multiple_submissions.data = problem.allow_multiple_submissions
    form.allow_more_submissions.data = problem.allow_more_submissions
    form.visible.data = problem.visible

    return render_template('teacher/classes/problem-edit.html', problem=problem, identifier=class_identifier, form=form,
                           class_=class_, page_title=f'Edit Problem - {problem.title} - {class_.name}')


# View a student's submission to a problem
@app.route('/teacher/submission/<task_id>', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_student_submission(task_id):
    # Get the submission and problem from the URL
    submission = Submission.query.filter_by(uuid=task_id).first_or_404()
    problem = submission.problem

    # If the problem's creator isn't the current user, them abort with a 404 error code
    if problem.user != current_user:
        abort(404)

    # Initialize the form
    form = UpdateMarkForm(problem.total_marks)

    # If the form was successfully submitted, update the student's mark for that submission
    if form.validate_on_submit():
        mark = form.mark.data
        submission.marks = round(float(mark), 2)
        db.session.commit()
        flash('The mark has been updated.', 'success')
        return redirect(url_for('teacher_student_submission', task_id=task_id))

    # Set the value in the form to be the student's existing mark for that submission
    form.mark.data = submission.marks

    # Generate a presigned URL for the student's code
    presigned_url = s3_client.generate_presigned_url('get_object',
                                                     Params={'Bucket': bucket_name, 'Key': submission.file_path},
                                                     ExpiresIn=3600)

    # Show a different page depending on whether the problem was auto graded or not
    if not problem.auto_grade:
        return render_template('teacher/classes/submission-plain.html', submission=submission,
                               presigned_url=presigned_url, class_=submission.problem.class_, form=form,
                               problem=problem,
                               page_title=f'Submission by {submission.student.name} - {problem.title} - {problem.class_.name}')

    results = submission.results

    return render_template('teacher/classes/submission.html', task_id=task_id, submission=submission,
                           time=problem.time_limit, presigned_url=presigned_url, results=results,
                           class_=submission.problem.class_, form=form, problem=problem,
                           page_title=f'Submission by {submission.student.name} - {problem.title} - {problem.class_.name}')


@app.route('/class/<string:class_identifier>/student/<string:student_identifier>', methods=['GET', 'POST'])
@login_required
@abort_teacher_not_confirmed
def teacher_class_specific_student(class_identifier, student_identifier):
    # Query the class from it's unique identifier, and if the class doesn't exist, abort with 404
    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    # Get the student
    student = Student.query.filter_by(identifier=student_identifier, class_=class_).first_or_404()

    # Get the student's average mark
    average_mark = get_student_mark(student, class_)

    # Get the student's submissions showing the latest one first
    submissions = sorted(student.submissions, key=lambda s: s.date_time, reverse=True)

    # Get the problems that the student has not submitted to, using simple list comprehension
    not_submitted = []

    for problem in class_.problems:
        not_submitted.append(problem) if student not in [s.student for s in problem.submissions] else None

    return render_template('teacher/classes/student.html', class_=class_, student=student, average_mark=average_mark,
                           submissions=submissions, not_submitted=not_submitted,
                           page_title=f'{student.name} - {class_.name}')


@app.route('/class/<string:class_identifier>/student/<string:student_identifier>/delete')
def teacher_class_delete_student(class_identifier, student_identifier):
    # If the user isn't logged in, don't tell them that this page exists!
    if not current_user.is_authenticated:
        abort(404)

    # Query the class from it's unique identifier, and if the class doesn't exist, abort with 404
    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    if class_ not in current_user.classes:
        abort(404)

    student = Student.query.filter_by(identifier=student_identifier, class_=class_).first_or_404()

    # Delete the student if the hashes match of the required attributes
    sha_hash_contents = sha256(f'{class_.id}{student.id}{current_user.password}'.encode('utf-8')).hexdigest()

    if sha_hash_contents != request.args.get('hash'):
        return render_template('errors/token_expired.html', page_title='Token expired'), 403

    db.session.delete(student)

    db.session.commit()

    # Let the user know, then redirect
    flash('The student has been deleted.', 'success')

    return redirect(url_for('teacher_class_home', identifier=class_identifier))
