from app import app, db
from app.models import Organization, Client, Event
from flask_login import current_user
from flask import flash, redirect, url_for
from datetime import date, datetime
from random import randint
import secrets
from PIL import Image
from email_validator import validate_email, EmailNotValidError
import bcrypt
import os


def get_badge_colors():
    badge_colors = ["bg-primary", "bg-secondary", "bg-success", "bg-warning", "bg-info", "bg-danger"]
    return badge_colors

def check_organization_status():
    if current_user.is_organization == True:
        if current_user.answered_organization_questions == True:
            return True
        else:
            flash("You must create your organization first by answering questions about it.", "warning")
            return redirect(url_for("orginfo", user_id=current_user.id))
    else:
        flash("You are not an administrator for an organization. Please contact your organization if you think this is a mistake.", "warning")
        return redirect(url_for("home"))

def check_age(dob, event_obj):
    today = date.today()
    dob = datetime(int(dob[0:4]), int(dob[5:7]), int(dob[8:]))
    user_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if int(event_obj.event_min_age) <= int(user_age) <= int(event_obj.event_max_age):
        return True
    else:
        return False

def check_max_participants_reached(event_obj):
    if int(len(event_obj.registrees)) + 1 <= int(event_obj.event_max_volunteers):
        return True
    else:
        return False

def get_random_code(n=6):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + str(f_ext)
    picture_path = os.path.join(app.root_path, 'static\images', picture_fn)
    output_size = (500, 500)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

def get_keywords_dict(list_of_keywords):
    kws_dict = {}
    item_num = 0

    for i in list_of_keywords:
        badge_colors = list(get_badge_colors())
        kws_dict[str(i)] = badge_colors[item_num]
        item_num += 1

    return kws_dict

def check_email(email, check_deliv):
    boolean_email_msg_return = []

    if email_unique(email) == True:

        try:
            emailinfo = validate_email(email, check_deliverability=check_deliv)

            email = emailinfo.normalized

            boolean_email_msg_return.append(True)
            boolean_email_msg_return.append(email)
            boolean_email_msg_return.append(None)

            return boolean_email_msg_return

        except EmailNotValidError as exception_description:
            boolean_email_msg_return.append(False)
            boolean_email_msg_return.append(email)
            boolean_email_msg_return.append(exception_description)

            return boolean_email_msg_return
        
    else:
        boolean_email_msg_return.append(False)
        boolean_email_msg_return.append(email)
        boolean_email_msg_return.append("That email already exists in our database. Please try again.")

        return boolean_email_msg_return

def email_unique(email):
    all_emails = get_all_emails()
    
    if email in all_emails:
        return False
    
    return True

def check_password(password_field, confirm_password_field):
    if password_field == confirm_password_field:
        return True
    else:
        return False

def get_is_organization_value(is_organization_field):
    if is_organization_field == "organization":
        return True
    
    return False

def get_all_organization_objs():
    all_org_objs = []

    for org in Organization.query.all():
        all_org_objs.append(org)

    return all_org_objs

def encrypt_password(password):
    new_password = ""

    password = password.encode("utf-8")
    new_password = bcrypt.hashpw(password, bcrypt.gensalt())

    return new_password

def get_all_emails():
    all_emails_list = []
    for user_obj in Client.query.all():
        all_emails_list.append(user_obj.email)
    return all_emails_list

def check_for_not_active_events():
    if current_user.is_authenticated:
        all_events = Event.query.all()
        for event in all_events:
            is_active = True

            current_time = convertto24(datetime.now().strftime("%I:%M:%S %p"))
            event_time = event.event_starttime

            current_date = str(date.today())
            event_date = str(date(int(event.event_startdate[0:4]), int(str(event.event_startdate)[5:7]), int(event.event_startdate[8:])))
            event_enddate = str(date(int(event.event_enddate[0:4]), int(str(event.event_enddate)[5:7]), int(event.event_enddate[8:])))

            current_datetime = str(datetime(int(current_date[0:4]), int(current_date[5:7]), int(current_date[8:]), int(current_time[0:2]), int(current_time[3:5])))
            event_datetime = str(datetime(int(event_date[0:4]), int(event_date[5:7]), int(event_date[8:]), int(event_time[0:2]), int(event_time[3:5])))

            event_enddate_datetime = str(datetime(int(event_enddate[0:4]), int(event_enddate[5:7]), int(event_enddate[8:]), int(event.event_endtime[0:2]), int(event.event_endtime[3:5])))

            if (current_datetime > event_datetime) and (current_datetime > event_enddate_datetime):
                is_active = False
            else:
                is_active = True
                
            if str(event.event_startdate) == str(event.event_enddate):
                display_datetime = datetime(int(event_date[0:4]), int(event_date[5:7]), int(event_date[8:])).strftime("%b %d")
            else:
                display_datetime = datetime(int(event_date[0:4]), int(event_date[5:7]), int(event_date[8:])).strftime("%b %d")
                display_datetime += " to " + str(datetime(int(event_enddate[0:4]), int(event_enddate[5:7]), int(event_enddate[8:])).strftime("%b %d"))

            display_datetime += ", " + str(datetime.strptime(f"{int(event_time[0:2])}:{int(event_time[3:5])}", "%H:%M").strftime("%I:%M %p"))
            display_datetime += " to " + str(datetime.strptime(f"{int(event.event_endtime[0:2])}:{int(event.event_endtime[3:5])}", "%H:%M").strftime("%I:%M %p"))

            event.for_display_event_datetime = display_datetime

            display_posttime = event.post_date + " at " + event.post_time
            event.for_display_post_datetime = display_posttime
            
            event.is_active = is_active

            delta = difference_between_dates(current_datetime, event_datetime, is_active)
            event.days_until_event = delta

            if event.last_updated == None or event.last_updated == "":
                event.last_updated = display_posttime

            db.session.commit()

def string_to_list(string_of_words):
    list_of_words = []

    list_of_words = list(str(string_of_words).strip("").split(","))

    return list_of_words

def convertto24(time_input): 
    if time_input[-2:] == "AM" and time_input[:2] == "12": 
        return "00" + time_input[2:-2] 
      
    elif time_input[-2:] == "AM": 
        return time_input[:-2] 
     
    elif time_input[-2:] == "PM" and time_input[:2] == "12": 
        return time_input[:-2] 
    
    else: 
        return str(int(time_input[:2]) + 12) + time_input[2:8]

def difference_between_dates(current_dt, event_dt, is_active):
    delta = ""

    cdt = datetime.strptime(current_dt, "%Y-%m-%d %H:%M:%S")
    edt = datetime.strptime(event_dt, "%Y-%m-%d %H:%M:%S")
    
    if is_active:
        delta = str((edt - cdt).days)
    else:
        delta = str((cdt - edt).days)

    return delta

