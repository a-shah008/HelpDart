from flask import Flask, render_template, flash, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField
from wtforms.validators import DataRequired

db = SQLAlchemy()

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

    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    return render_template("register.html")


class Client(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    is_organization = db.Column(db.Boolean, default=False)

    full_name = db.Column(db.String(60))
    email = db.Column(db.String(120))
    password = db.Column(db.String(60))

    confirmed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        output = ""
        if self.is_organization == True:
            output = ": Organization"
        else:
            output = ": Customer"

        return f"{self.full_name}{output}"

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])

if __name__ == "__main__":
    app.run(debug=True)

