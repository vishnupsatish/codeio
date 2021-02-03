import boto3
import mistune
from hashlib import sha256
from secrets import token_urlsafe
from flask import render_template, url_for, flash, redirect, request, abort
from application import app, db, bcrypt, admin
from flask_login import login_user, current_user, logout_user, login_required
from flask_admin.contrib.sqla import ModelView
from application.forms.teacher import *
from application.settingssecrets import *
from application.models.general import *
from application.utils import *

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Student, db.session))
admin.add_view(ModelView(Class_, db.session))
admin.add_view(ModelView(Problem, db.session))
admin.add_view(ModelView(Language, db.session))
admin.add_view(ModelView(InputFile, db.session))
admin.add_view(ModelView(OutputFile, db.session))
admin.add_view(ModelView(Submission, db.session))
admin.add_view(ModelView(Result, db.session))

# Initialize AWS's Python SDK (Boto3) resource (higher-level API) with the access key and secret access key
s3 = boto3.resource('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# Initialize AWS's Python SDK (Boto3) client (lower-level API) with the access key and secret access key
s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name='ca-central-1')

# Set AWS bucket name
bucket_name = 'code-execution-grade-10'


@app.context_processor
def send_sha_function():
    return {'sha256': sha256}


# If the user goes to "/", redirect to the dashboard
@app.route('/')
def teacher_redirect_to_dashboard():
    return redirect(url_for('teacher_dashboard'))


# Log the user out
@app.route('/logout')
def logout():
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

    # If form was submitted successfully, create a user and redirect to login page
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')
        user = User(name=form.name.data, email=form.email.data,
                    password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('teacher_login'))

    return render_template('teacher/general/register.html', form=form)


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
    return render_template('teacher/general/login.html', form=form)


# The teacher's dashboard
@app.route('/dashboard')
@login_required
def teacher_dashboard():
    # Get all of the classes that are associated to the current user
    classes_ = Class_.query.filter_by(user=current_user).all()
    return render_template('teacher/general/dashboard.html', classes_=classes_)


# Creating a new class
@app.route('/new-class', methods=['GET', 'POST'])
@login_required
def new_class():
    # Initialize the NewClassForm from Flask-WTF
    form = NewClassForm()
    if form.validate_on_submit():
        # If the form was successfully submitted, create a new class and Flash the result to the user
        class_ = Class_(name=form.name.data, description=form.description.data, user=current_user,
                        identifier=token_urlsafe(16))
        db.session.add(class_)
        db.session.commit()
        flash('The class has been created successfully.', 'success')
        return redirect(url_for('teacher_dashboard'))
    return render_template('teacher/general/new-class.html', form=form)


# A class's homepage
@app.route('/class/<string:identifier>/home')
@login_required
def teacher_class_home(identifier):
    # Query the class from it's unique identifier, and if the class doesn't exist, abort with 404
    class_ = Class_.query.filter_by(identifier=identifier, user=current_user).first_or_404()

    # Get all of the problems associated to that class
    problems = Problem.query.filter_by(class_=class_).order_by(Problem.create_date_time.desc()).all()

    # Call a utility function which, for each problem, gets the
    # number of unique students that have submitted the problem
    u = get_unique_students_problem(problems)
    return render_template('teacher/classes/home.html', problems=problems, class_=class_, identifier=identifier, u=u)


# A route for deleting a class (uses hashing to ensure the user themselves requested the deletion
@app.route('/class/<string:identifier>/delete')
def teacher_class_delete(identifier):
    # If the user isn't logged in, don't tell them that this page exists!
    if not current_user.is_authenticated:
        abort(404)

    # Query the class from it's unique identifier, and if the class doesn't exist, abort with 404
    class_ = Class_.query.filter_by(identifier=identifier, user=current_user).first_or_404()

    # Hash the same properties as was passed from the class page
    sha_hash_contents = sha256(
        f'{class_.identifier}{class_.id}{current_user.password}'.encode('utf-8')).hexdigest()

    # if the two hashes are not the same, then abort with a 404 exit code
    if sha_hash_contents != request.args.get('hash'):
        return 'Incorrect deletion hash.'

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
@app.route('/class/<string:identifier>/students', methods=['GET', 'POST'])
@login_required
def teacher_class_students(identifier):
    # Get the class from the identifier in the URL
    class_ = Class_.query.filter_by(identifier=identifier, user=current_user).first_or_404()

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

    return render_template('teacher/classes/students.html', identifier=identifier, form=form, class_=class_,
                           students=students, marks=marks)


# Creating a new problem
@app.route('/class/<string:identifier>/new-problem', methods=['GET', 'POST'])
@login_required
def teacher_class_new_problem(identifier):
    class_ = Class_.query.filter_by(identifier=identifier, user=current_user).first_or_404()
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

        # For every langauge that the user chose, get the corresponding database
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

    return render_template('teacher/classes/new-problem.html', form=form, identifier=identifier, class_=class_)


# Each problem's page
@app.route('/class/<string:class_identifier>/problem/<string:problem_identifier>', methods=['GET', 'POST'])
@login_required
def teacher_class_problem(class_identifier, problem_identifier):
    # Get the class the problem from the database based on each identifier as passed in from the URL
    class_ = Class_.query.filter_by(identifier=class_identifier, user=current_user).first_or_404()
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
                           active_show_problem=active_show_problem)


# Route to delete a problem
@app.route('/class/<string:class_identifier>/problem/<string:problem_identifier>/delete')
def teacher_class_problem_delete(class_identifier, problem_identifier):
    if not current_user.is_authenticated:
        abort(404)

    # Get the class and problem
    class_ = Class_.query.filter_by(identifier=class_identifier, user=current_user).first_or_404()
    problem = Problem.query.filter_by(identifier=problem_identifier, user=current_user, class_=class_).first_or_404()

    # Hash the same properties as was passed from the problem page
    sha_hash_contents = sha256(
        f'{class_.identifier}{class_.id}{problem.identifier}{problem.id}{current_user.password}'.encode(
            'utf-8')).hexdigest()

    # if the two hashes are not the same, then abort with a 404 exit code
    if sha_hash_contents != request.args.get('hash'):
        return 'Incorrect deletion hash.'

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
def teacher_class_problem_edit(class_identifier, problem_identifier):
    # Get the class the problem from the database based on each identifier as passed in from the URL
    class_ = Class_.query.filter_by(identifier=class_identifier, user=current_user).first_or_404()
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

        return redirect(url_for('teacher_class_problem_edit', class_identifier=class_identifier,
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
                           class_=class_)


# View a student's submission to a problem
@app.route('/teacher/submission/<task_id>', methods=['GET', 'POST'])
@login_required
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
                               problem=problem)

    results = submission.results

    return render_template('teacher/classes/submission.html', task_id=task_id, submission=submission,
                           time=problem.time_limit, presigned_url=presigned_url, results=results,
                           class_=submission.problem.class_, form=form, problem=problem)
