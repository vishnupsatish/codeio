from application.models.general import Language


def get_languages_form():
    langs = Language.query.all()
    languages = []
    for l in langs:
        languages.append((l.number, l.name))

    return languages