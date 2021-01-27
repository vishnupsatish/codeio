from application.models.general import Language, Submission, InputFile, OutputFile
from application import db
import uuid
import datetime as dt
import time as tm
from mimetypes import guess_type
from werkzeug.utils import secure_filename


def get_languages_form():
    langs = Language.query.all()
    languages = []
    for l in langs:
        languages.append((l.number, l.name))

    return languages


def get_unique_students_problem(problems):
    u = {}
    for p in problems:
        u[p] = []
        submissions = Submission.query.filter_by(problem=p).all()
        for s in submissions:
            if s.student.identifier not in u[p]:
                u[p].append(s.student.identifier)
        u[p] = len(u[p])
    return u


def upload_input_output_file(num, input_file_object, output_file_object, class_, problem, s3, bucket_name):
    if not input_file_object:
        return
    input_file_data = input_file_object.read()
    output_file_data = output_file_object.read()
    if len(input_file_data) / 1000000 > 1 or len(output_file_data) / 1000000 > 1:
        return 'The maximum file size you can add is 1 megabyte.'
    input_file_path = f'classes/{class_.identifier}/problems/{problem.identifier}/input_files/input{num}.txt'
    inp = InputFile(number=num, file_path=input_file_path, file_size=len(input_file_data), problem=problem)

    s3_object = s3.Object(bucket_name, input_file_path)
    s3_object.put(Body=input_file_data, ContentType='text/plain')

    output_file_path = f'classes/{class_.identifier}/problems/{problem.identifier}/output_files/output{num}.txt'
    out = OutputFile(number=num, file_path=output_file_path, file_size=len(output_file_data), problem=problem)

    s3_object = s3.Object(bucket_name, output_file_path)
    s3_object.put(Body=output_file_data, ContentType='text/plain')

    inp.output_file = out

    db.session.add(inp)
    db.session.add(out)

    db.session.commit()


def upload_submission_file(language, submission_file_object, class_, problem, s3, bucket_name, student,
                           uuid=str(uuid.uuid4())):
    submission_file_data = submission_file_object.read()
    if len(submission_file_data) / 1000000 > 1:
        return 'The maximum file size you can add is 1 megabyte.'

    language = Language.query.filter_by(number=language).first()
    submission_file_path = f'classes/{class_.identifier}/problems/{problem.identifier}/submissions/{secure_filename(student.name)}-{student.id}-{int(tm.time())}.{language.file_extension}'
    mimetype = guess_type(submission_file_path)[0]
    s3_object = s3.Object(bucket_name, submission_file_path)
    s3_object.put(Body=submission_file_data, ContentType=mimetype)

    submission = Submission(file_path=submission_file_path, file_size=len(submission_file_data), problem=problem,
                            student=student, language=language, uuid=uuid)
    db.session.add(submission)
    db.session.commit()
