from application.models.general import Language, Submission


def get_languages_form():
    langs = Language.query.all()
    languages = []
    for l in langs:
        languages.append((l.number, l.name))

    return languages


def get_unqiue_students_problem(problems):
    u = {}
    for p in problems:
        u[p] = []
        submissions = Submission.query.filter_by(problem=p).all()
        for s in submissions:
            u[p].append(s.user.email) if s.user.email not in s else 0
        u[p] = len(u[p])
    return u