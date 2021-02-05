import os
import boto3
import mistune
from hashlib import sha256
from secrets import token_urlsafe
from functools import wraps
from flask import render_template, url_for, flash, redirect, request, abort, send_from_directory, send_file
from application import app, db, bcrypt, mail, serializer
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
    return redirect(url_for('teacher_login'))


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
@app.route('/register', methods=['GET', 'POST'])
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
                    password=hashed_password, confirm=True)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        token = serializer.dumps(current_user.email, salt=os.environ.get('SECRET_KEY'))

        # Resend confirmation email, if there was an error, say so
        try:
            mail.send_message(sender='contact@codeio.tech',
                              subject='Your CodeIO Confirmation Email',
                              body=f'Click on the below link to confirm your CodeIO account\n{request.host_url[:-1]}/token/{token}',
                              recipients=[current_user.email])
        except:
            flash('There was an error sending a confirmation email.', 'danger')

        return redirect(url_for('teacher_login'))

    return render_template('teacher/general/register.html', form=form, page_title='Register')


# Login page
@app.route('/login', methods=['GET', 'POST'])
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
                              body=f'Click on the below link to confirm your CodeIO account\n{request.host_url[:-1]}/token/{token}',
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
    # If the user is not logged in or the user has already confirmed, then return
    if not current_user.is_authenticated:
        abort(404)

    if current_user.confirm:
        abort(404)

    # Load the token, then check if the emails match and set that the user has confirmed
    try:
        email = serializer.loads(token, salt=os.environ.get('SECRET_KEY'), max_age=7200)
        if email == current_user.email:
            current_user.confirm = True
            db.session.commit()

            flash('Your email has been confirmed.', 'success')
            return redirect(url_for('teacher_dashboard'))
    # If there was an error while loading the token, return so
    except:
        return render_template('errors/token_expired.html'), 403


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
    # game, and generate a urlsafe code that the student will use to log in
    if form.validate_on_submit():
        student = Student(name=form.name.data, identifier=token_urlsafe(4), class_=class_)
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
                           base_url=request.host_url[:-1], students=students, marks=marks,
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
        return render_template('errors/token_expired.html'), 403

    # If the user is requesting to the join the incorrect class, let the user know and abort with a 404
    if serial_encrypt != class_.id:
        return render_template('errors/token_expired.html'), 403

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
                          identifier=token_urlsafe(8), class_=class_, description_html=description_html)

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

    return render_template('teacher/classes/problem.html', problem=problem, identifier=class_identifier,
                           input_presigned_urls=input_presigned_urls, output_presigned_urls=output_presigned_urls,
                           class_=class_, student_submissions=student_submissions, base_url=request.host_url[:-1],
                           active_student_submissions=active_student_submissions,
                           show_student_submissions=show_student_submissions, show_problem_info=show_problem_info,
                           active_show_problem=active_show_problem, page_title=f'{problem.title} - {class_.name}')


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
        return render_template('errors/token_expired.html'), 403

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
