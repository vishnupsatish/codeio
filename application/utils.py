from application.models.general import Language, Submission, InputFile, OutputFile
from application import db


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
            u[p].append(s.user.email) if s.user.email not in s else 0
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

    object = s3.Object(bucket_name, input_file_path)
    object.put(Body=input_file_data, ContentType='text/plain')

    output_file_path = f'classes/{class_.identifier}/problems/{problem.identifier}/output_files/output{num}.txt'
    out = OutputFile(number=num, file_path=output_file_path, file_size=len(output_file_data), problem=problem)

    object = s3.Object(bucket_name, output_file_path)
    object.put(Body=output_file_data, ContentType='text/plain')

    inp.output_file = out

    db.session.add(inp)
    db.session.add(out)

    db.session.commit()
