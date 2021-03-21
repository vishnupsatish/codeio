from application.models.general import Language, Submission, InputFile, OutputFile
from application import db
import uuid
import time as tm
from mimetypes import guess_type
from werkzeug.utils import secure_filename


# Get a tuple of (language.id, language.name), the former of which will be
# returned when the form is submitted and the latter of which will the shown to the user
def get_languages_form():
    langs = Language.query.all()
    languages = []
    for l in langs:
        languages.append((l.number, l.name))

    return languages


# Get the number of unique students that have submitted each problem
def get_unique_students_problem(problems):
    u = {}

    # For every problem
    for p in problems:
        u[p] = []

        # Get all of the submission of the problem
        submissions = Submission.query.filter_by(problem=p).all()

        # Only add that submission's student's identifier if it does not already exist
        for s in submissions:
            if s.student.identifier not in u[p]:
                u[p].append(s.student.identifier)

        # Get the number of unique students that have submitted the problem, and not the students themselves
        u[p] = len(u[p])

    return u


# Upload the input and it's corresponding output file
def upload_input_output_file(num, input_file_object, output_file_object, class_, problem, s3, bucket_name):
    # If the user has not uploaded an input file, return None
    if not input_file_object:
        return

    # Read both of the files
    input_file_data = input_file_object.read()
    output_file_data = output_file_object.read()

    # If the files are too large, return the string to be flashed
    if len(input_file_data) / 8000000 > 1 or len(output_file_data) / 8000000 > 1:
        return 'The maximum file size you can add is 8 megabytes.'

    # Generate the input file path based on the class, problem, and the number of the file
    input_file_path = f'classes/{class_.identifier}/problems/{problem.identifier}/input_files/input{num}.txt'

    # Create the input file's database object with its attributes, then associate it to the problem
    inp = InputFile(number=num, file_path=input_file_path, file_size=len(input_file_data), problem=problem)

    # Upload the input file to AWS S3 with the mimetype being "text/plain"
    # so the user can view the file without needing to download it
    s3_object = s3.Object(bucket_name, input_file_path)
    s3_object.put(Body=input_file_data, ContentType='text/plain')

    # Create the output file's database object with its attributes, then associate it to the problem
    output_file_path = f'classes/{class_.identifier}/problems/{problem.identifier}/output_files/output{num}.txt'
    out = OutputFile(number=num, file_path=output_file_path, file_size=len(output_file_data), problem=problem)

    # Upload the output file to AWS S3 with the mimetype being "text/plain"
    # so the user can view the file without needing to download it
    s3_object = s3.Object(bucket_name, output_file_path)
    s3_object.put(Body=output_file_data, ContentType='text/plain')

    # Associate the output file with the input file
    inp.output_file = out

    # Add the input and output files, then commit
    db.session.add(inp)
    db.session.add(out)

    db.session.commit()


# Ipload the student's submission file
def upload_submission_file(language, submission_file_object, class_, problem, s3, bucket_name, student,
                           uuid_=None):
    # In some cases, such as if the submission is being auto
    # graded, the UUID parameter will contain the Celery task's task id
    if uuid_ is None:
        uuid_ = str(uuid.uuid4())

    # Get the text from the submission file
    submission_file_data = submission_file_object.read()

    # If the file is too large, return the text to be flashed
    if len(submission_file_data) / 5000000 > 1:
        return 'The maximum file size you can add is 1 megabyte.'

    # Get the language that the student submitted in
    language = Language.query.filter_by(number=language).first()

    # Create the file path to be stored in AWS based on the class, problem,
    # student, and the current UNIX Timestamp (seconds from Jan 1, 1970)
    submission_file_path = f'classes/{class_.identifier}/problems/{problem.identifier}/submissions/{secure_filename(student.name)}-{student.id}-{int(tm.time())}.{language.file_extension}'
    # mimetype = guess_type(submission_file_path)[0]
    # if mimetype is None:
    #     mimetype = 'text/plain'

    # Upload the file with the mimetype "text/plain", so the user can view the file on S3 without needing to download it
    mimetype = 'text/plain'
    s3_object = s3.Object(bucket_name, submission_file_path)
    s3_object.put(Body=submission_file_data, ContentType=mimetype)

    # Create the submission DB object, then add and commit it
    submission = Submission(file_path=submission_file_path, file_size=len(submission_file_data), problem=problem,
                            student=student, language=language, uuid=uuid_)
    db.session.add(submission)
    db.session.commit()

    # Return the submission and the UUID (has an _ to prevent the name from clashing with the module UUID)
    return submission, uuid_


# Get a given student's average mark based on their highest submission for each problem
def get_student_mark(student, class_):
    # Get every problem associated to the class
    problems = class_.problems
    marks = [0, 0, '0%']

    # Iterate over each problem
    for p in problems:
        try:
            # Filter the submissions in the problem such that the user that submitted
            # it is the student to get the highest mark from, then get the highest mark
            # using the max function and the key to check being the marks that the submission earned
            submissions = Submission.query.filter_by(problem=p, done=True).all()
            max_mark_submissions = max(list(filter(lambda a: a.student == student, submissions)),
                                       key=lambda s: s.marks)

        # This error occurs if the student has made no submissions to the
        # problem, since you cannot file the max element of an empty list
        except ValueError:
            continue

        # Add the highest submission's marks as well as the total marks of the problem to the list to return
        marks[0] += max_mark_submissions.marks
        marks[1] += p.total_marks

    # If the student has done at least one problem, calculate their average
    # percentage, else keep it as 0 to avoid throwing a ZeroDivisionError
    if marks[1] != 0:
        marks[2] = f'{round(marks[0] / marks[1] * 100, 2)}%'

    return marks


# Delete all input and output files associated with a problem
def delete_input_output_files(problem, s3, bucket_name):
    for input_file in problem.input_files:
        s3.Object(bucket_name, input_file.file_path).delete()

    for output_file in problem.output_files:
        s3.Object(bucket_name, output_file.file_path).delete()


# Delete all submission files associated with a problem
def delete_submission_files(problem, s3, bucket_name, files=None):
    if not files:
        files = problem.submissions

    for submission in files:
        s3.Object(bucket_name, submission.file_path).delete()
