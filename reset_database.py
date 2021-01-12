import datetime as dt
from application import db, bcrypt
from application.models.general import *
from application.models.class_ import *

db.drop_all()
db.create_all()

school = School(name="XY School")

epoch_time = int(dt.datetime.now().timestamp())

user1 = User(username="aa", email="a@a.a", password=bcrypt.generate_password_hash("aa").decode('utf-8'), admin=True,
             name="Aa Aa", create_date_time=epoch_time, school=school)
user2 = User(username="bb", email="b@b.b", password=bcrypt.generate_password_hash("bb").decode('utf-8'), student=True,
             name="Bb Bb", create_date_time=epoch_time, school=school)
user3 = User(username="cc", email="c@c.c", password=bcrypt.generate_password_hash("cc").decode('utf-8'), student=True,
             name="Cc Cc", create_date_time=epoch_time, school=school)

announcement1 = Announcement(create_date_time=epoch_time,
                             text="Hello students, please learn how to code.",
                             user=user1, school=school)

announcement1link1 = AnnouncementLink(url="https://stackoverflow.com", announcement=announcement1,
                                      name="Coding Questions - Stack Overflow")

announcement2 = Announcement(create_date_time=epoch_time, text="Hello teacher can you please help me? Thanks.", user=user2,
                             school=school)

class1 = Class_(create_date_time=epoch_time, name="Class with Bb Bb", school=school)

class1.users.append(user1)
class1.users.append(user2)

schedule1 = Schedule(day="Friday", timezone=300, start_time=dt.time(hour=7, minute=30),
                     end_time=dt.time(hour=8, minute=30), class_=class1, school=school)

content1 = Content(create_date_time=epoch_time,
                   text="Hello Bb, hope you are fine, your class is now scheduled for Friday 7:30 pm Eastern Time.",
                   class_=class1, user=user1)

db.session.add_all(
    [school, user1, user2, user3, announcement1, announcement1link1, announcement2, class1, schedule1, content1])

db.session.commit()
