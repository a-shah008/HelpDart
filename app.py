from flask import Flask, render_template, flash, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SubmitField, TextAreaField, SelectField, DateField, TimeField
from wtforms.validators import InputRequired, ValidationError
from email_validator import validate_email, EmailNotValidError
from datetime import date, datetime
import bcrypt
from fuzzywuzzy import fuzz, process

db = SQLAlchemy()

event_categories = ["Animals/Veterinary", "Religious", "Medical", "Military", "Arts/Literature", "Sports", "Youth/Education", "Nature/Outdoors", "Community", "Philanthropy/General", "Other"]

def create_app():
    app = Flask(__name__)
    
    app.config["SECRET_KEY"] = "helpdart"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
    
    db.init_app(app)

    return app

app = create_app()
app.app_context().push()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Client.query.get(int(user_id))

@app.route("/", methods=["GET", "POST"])    
@app.route("/home", methods=["GET", "POST"])
def home():
    all_events = Event.query.all()

    return render_template("home.html", all_events=all_events)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    
    if request.method == "POST":
        if form.validate_on_submit():
            user_email = form.email.data
            user_password = form.password.data
            signed_up_user_emails = get_all_emails()
            
            if user_email in signed_up_user_emails:
                if bcrypt.checkpw(user_password.encode("utf-8"), Client.query.filter_by(email=user_email).first().password):
                    login_user(Client.query.filter_by(email=user_email).first())
                    flash("You have been successfully logged in.", "success")
                    return redirect(url_for("home"))
                else:
                    flash("Incorrect password, please try again.", "warning")
                    return redirect(url_for("login"))
            else:
                flash("You have not registered yet.", "warning")
                return redirect(url_for("register"))

    return render_template("login.html", form=form)

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if request.method == "POST":
        if form.validate_on_submit():
            user_fullname = form.fullname.data
            user_email = form.email.data
            user_password = form.password.data
            user_confirm_password = form.confirm_password.data
            user_is_organization = get_is_organization_value(request.form.get("is_organization"))

            email_check_list = check_email(user_email, True)
            user_email = email_check_list[1]
            password_check = check_password(user_password, user_confirm_password)

            if email_check_list[0] == False:
                flash("There was an issue with your email. Please try again.", "warning")
                return redirect(url_for("register"))
            elif password_check == False:
                flash("Your passwords do not match. Please try again.", "warning")
                return redirect(url_for("register"))
            
            new_user = Client(is_organization=user_is_organization, full_name=user_fullname, email=user_email, password=encrypt_password(user_password))
            db.session.add(new_user)
            db.session.commit()
            login_user(Client.query.filter_by(email=user_email).first())
            flash("You have been successfully registered!", "success")
            return redirect(url_for("home"))

    return render_template("register.html", form=form)

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateAccountForm()

    if request.method == "GET":
        form.fullname.data = current_user.full_name
        form.email.data = current_user.email

    else:
        if form.validate_on_submit():
            new_user_fullname = form.fullname.data
            new_user_email = form.email.data

            if new_user_email != current_user.email:
                email_check_list = check_email(new_user_email, True)
                new_user_email = email_check_list[1]

                if email_check_list[0] == False:
                    flash("There was an issue with your email. Please try again.", "warning")
                    return redirect(url_for("account"))
            else:
                new_user_email = form.email.data
            
            current_user.full_name = new_user_fullname
            current_user.email = new_user_email
            db.session.commit()
            flash("Your account information has been successfully updated!", "success")
            return redirect(url_for("account"))

    return render_template("account.html", form=form)

@app.route("/post", methods=["GET", "POST"])
@login_required
def post():
    form = CreateNewPostForm()

    if request.method == "GET":
        current_date = date.today()
        current_date_output = f"{current_date.month}/{current_date.day}/{current_date.year}"
        current_time = datetime.now().strftime("%H:%M")

        return render_template("post.html", form=form, current_date=current_date_output, current_time=current_time)
    
    else:
        current_post_time = datetime.now().strftime("%I:%M:%S %p")
        current_post_date = date.today().strftime("%b %d, %Y")

        if (request.form.get("post_startdate") == "" or request.form.get("post_startdate") == None) or (request.form.get("post_enddate") == "" or request.form.get("post_enddate") == None) or (request.form.get("post_starttime") == "" or request.form.get("post_starttime") == None) or (request.form.get("post_endtime") == "" or request.form.get("post_endtime") == None):
            flash("Please enter a valid start/end date/time. Try again.", "warning")
            return redirect(url_for("post"))
        else:
            new_event = Event(event_name=form.name.data, event_startdate=request.form.get("post_startdate"), event_enddate=request.form.get("post_enddate"), event_starttime=request.form.get("post_starttime"), event_endtime=request.form.get("post_endtime"), event_location=form.location.data, event_max_volunteers=form.max_volunteers.data, event_category=form.category.data, event_description=form.description.data, post_date=current_post_date, post_time=current_post_time, organizer_id=current_user.id)
            db.session.add(new_event)
            db.session.commit()
            flash("Event has been successfully posted.", "success")
            return redirect(url_for("view_posts"))

@app.route("/view_posts", methods=["GET", "POST"])
@login_required
def view_posts():
    check_for_not_active_events()
    active_events = []
    inactive_events = []
    form = EditPostBtn()

    for i in Event.query.filter_by(is_active=True).all():
        active_events.append(i)

    for j in Event.query.filter_by(is_active=False).all():
        inactive_events.append(j)

    if request.method == "POST":
        post_id = request.form.get("edit_post_btn")
        return redirect(url_for("edit_post", post_id=post_id))

    return render_template("view_posts.html", active_events=active_events, inactive_events=inactive_events, editbtnform=form)

@app.route("/edit_post/<post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    form = EditPostForm()
    post_obj = Event.query.filter_by(id=post_id).first()

    if request.method == "GET":
        form.name.data = post_obj.event_name
        post_startdate = post_obj.event_startdate
        post_enddate = post_obj.event_enddate
        post_starttime = post_obj.event_starttime
        post_endtime = post_obj.event_endtime
        form.location.data = post_obj.event_location
        form.max_volunteers.data = post_obj.event_max_volunteers
        form.category.data = post_obj.event_category
        form.description.data = post_obj.event_description
    elif request.method == "POST":
        post_obj.event_name = form.name.data
        post_obj.event_startdate = request.form.get("post_startdate")
        post_obj.event_enddate = request.form.get("post_enddate")
        post_obj.event_starttime = request.form.get("post_starttime")
        post_obj.event_endtime = request.form.get("post_endtime")
        post_obj.event_location = form.location.data
        post_obj.event_max_volunteers = form.max_volunteers.data
        post_obj.event_category = form.category.data
        post_obj.event_description = form.description.data

        post_obj.last_updated = str(datetime.now().date().strftime("%b %d, %Y")) + " at " + str(datetime.now().time().strftime("%I:%M:%S %p"))

        db.session.commit()
        
        flash("Post has been successfully updated.", "success")
        return redirect(url_for("view_posts"))

    return render_template("edit_post.html", form=form, post_startdate=post_startdate, post_enddate=post_enddate, post_starttime=post_starttime, post_endtime=post_endtime)

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for("home"))

class Client(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    is_organization = db.Column(db.Boolean, default=False)

    full_name = db.Column(db.String(60))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(60))

    events = db.relationship("Event", backref="organizer")
    
    def __repr__(self):
        output = ""
        if self.is_organization == True:
            output = ": Organization"
        else:
            output = ": Customer"

        return f"{self.full_name} ({self.email}){output}"
    
class Event(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    event_name = db.Column(db.String(120))
    event_startdate = db.Column(db.String(120))
    event_enddate = db.Column(db.String(120))
    event_starttime = db.Column(db.String(120))
    event_endtime = db.Column(db.String(120))
    event_location = db.Column(db.String(120))
    event_max_volunteers = db.Column(db.String(120))
    event_category = db.Column(db.String(120))
    event_description = db.Column(db.String(120))

    post_date = db.Column(db.String(120))
    post_time = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    for_display_event_datetime = db.Column(db.String(120))
    for_display_post_datetime = db.Column(db.String(120))
    days_until_event = db.Column(db.String(120))
    last_updated = db.Column(db.String(120))

    organizer_id = db.Column(db.Integer, db.ForeignKey("client.id"))

    def __repr__(self):
        return f"\n\nPost Information:\n{self.event_name},\n{self.event_startdate} to {self.event_enddate},\n{self.event_starttime} to {self.event_endtime},\n{self.event_location},\n{self.event_ideal_num_of_volunteers},\n{self.event_category},\n{self.event_description}\n\n Metadata:\nCreated: {self.post_date}, {self.post_time}\nOrganized By: {Client.query.filter_by(id=self.organizer_id).first()}\n\n\n"

class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])

    submit = SubmitField("Login")

class RegisterForm(FlaskForm):
    fullname = StringField("Full Name", validators=[InputRequired()])
    email = EmailField("Email", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[InputRequired()])

    submit = SubmitField("Register")

class UpdateAccountForm(FlaskForm):
    fullname = StringField("Full Name")
    email = EmailField("Email")

    submit = SubmitField("Save")

class CreateNewPostForm(FlaskForm):
    name = StringField("Event Name:", validators=[InputRequired()])
    startdate = StringField("Event Start Date:", validators=[InputRequired()])
    enddate = StringField("Event End Date:", validators=[InputRequired()])
    starttime = StringField("Event Start Time:", validators=[InputRequired()])
    endtime = StringField("Event End Time:", validators=[InputRequired()])
    location = StringField("Event Location:", validators=[InputRequired()])
    max_volunteers = StringField("Max Number of Volunteers:", validators=[InputRequired()])
    category = SelectField("Category:", choices=list(["Pick a category..."] + event_categories))
    description = TextAreaField("Brief Description:", validators=[InputRequired()])

    submit = SubmitField("Save")

    def validate_category(category):
        if category.data == "Pick a category...":
            raise ValidationError("Pick a valid category. Please try again.")

class EditPostBtn(FlaskForm):

    editbtn = SubmitField("Edit")

class EditPostForm(FlaskForm):
    name = StringField("Event Name:", validators=[InputRequired()])
    startdate = StringField("Event Start Date:", validators=[InputRequired()])
    enddate = StringField("Event End Date:", validators=[InputRequired()])
    starttime = StringField("Event Start Time:", validators=[InputRequired()])
    endtime = StringField("Event End Time:", validators=[InputRequired()])
    location = StringField("Event Location:", validators=[InputRequired()])
    max_volunteers = StringField("Max Number of Volunteers:", validators=[InputRequired()])
    category = SelectField("Category:", choices=list(["Pick a category..."] + event_categories))
    description = TextAreaField("Brief Description:", validators=[InputRequired()])

    submit = SubmitField("Save")

    def validate_category(category):
        if category.data == "Pick a category...":
            raise ValidationError("Pick a valid category. Please try again.")

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
    if current_user.is_authenticated and current_user.is_organization:
        all_organizer_events = Event.query.filter_by(organizer_id=current_user.id)
        for event in all_organizer_events:
            is_active = True

            current_time = convertto24(datetime.now().strftime("%I:%M:%S %p"))
            event_time = event.event_starttime

            current_date = str(date.today())
            event_date = str(date(int(event.event_startdate[0:4]), int(str(event.event_startdate)[5:7]), int(event.event_startdate[8:])))
            event_enddate = str(date(int(event.event_enddate[0:4]), int(str(event.event_enddate)[5:7]), int(event.event_enddate[8:])))

            current_datetime = str(datetime(int(current_date[0:4]), int(current_date[5:7]), int(current_date[8:]), int(current_time[0:2]), int(current_time[3:5])))
            event_datetime = str(datetime(int(event_date[0:4]), int(event_date[5:7]), int(event_date[8:]), int(event_time[0:2]), int(event_time[3:5])))
            
            if current_datetime > event_datetime:
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
 
    else:
        flash("There was an issue loading the results. Please try again later.", "warning")
        return redirect(url_for("home"))


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

if __name__ == "__main__":
    app.run(debug=True)

