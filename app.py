from flask import Flask, render_template, request, redirect, url_for, flash, session
from scraper import run_scraper, get_dates, get_available_dates, get_available_mensas, scraper, url_dict
import os
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from secret import PASSWORD, USER, HOST, PORT, MAIL_USERNAME,MAIL_PASSWORD, APP_SECRET_KEY


# Ensure the 'generated_images' folder exists
current_dir = os.path.dirname(os.path.abspath(__file__))
images_folder = os.path.join(current_dir, 'static', 'generated_images')
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

app = Flask(__name__, static_folder='static')

app.secret_key = APP_SECRET_KEY

################################# set up Email SMTP for contact us page #######################################
app.config['MAIL_SERVER']= "smtp.gmail.com"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD

################################ postgresql database ##########################################################
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/postgres"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

mail = Mail(app)
db = SQLAlchemy(app)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
   return render_template('about.html')

@app.route('/review')
def review():
   return render_template('review.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():

    if request.method == 'POST':

        # get email and message data from frontend
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        if not name or not email or not message:
            flash('All fields are required!', 'error')
            return redirect(url_for('contact'))

        # Send email
        try:
            msg = Message(subject=f"Contact Form Submission from {name}",
                          body=f'Name: {name}\nEmail: {email}\n\nMessage:\n{message}',
                          sender=MAIL_USERNAME,
                          recipients=['mensaapptuebingen@gmail.com'])
            
            mail.send(msg)

            flash('Message sent successfully!', 'success')
        except Exception as e:
            flash(f'Failed to send message: {str(e)}', 'error')

        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/dining_facilities')
def dining_facilities():
    available_dates = get_available_dates()
    available_mensas = get_available_mensas()
    return render_template('dining_facilities.html', available_dates=available_dates, available_mensas=available_mensas)

@app.route('/mensa/<mensa_name>')
def mensa_menu(mensa_name):
    selected_date = request.args.get('date')
    if not selected_date:
        return "Date not provided", 400
    scraper_res = run_scraper(mensa_name, selected_date)  
    all_dishes = scraper_res[["menuLine", "menu", "studentPrice", "image_filename"]].to_dict(orient="records")
    return render_template('mensa_result.html', all_dishes=all_dishes, selected_option=mensa_name, selected_date=selected_date)

@app.route('/scrape_all')
def scrape_all():
    available_dates = get_available_dates()
    available_mensas = get_available_mensas()
    scraper(available_dates, available_mensas, url_dict)
    return "Scraping completed for all dates and mensas."

@app.route('/check_image/<filename>')
def check_image(filename):
    image_path = os.path.join(images_folder, filename)
    if os.path.exists(image_path):
        return '', 200
    else:
        return '', 404

@app.route('/menu_maker')
def menu_maker():
   return render_template('menu_maker.html')


# Database model: Each object of the User class creates a new column in the User table
class User(db.Model):
    # class variables
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=True)

    # set a new password but safe password hash, not the password itself in db for security reasons
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # check if password is correct
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# check username and password that user puts into form with db
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        # collect user login data from frontend form
        username = request.form['username']
        password = request.form['password']

        # search for username in database
        user = User.query.filter_by(username=username).first()

        # if user name exists and password is correct: log user in
        if user and user.check_password(password):
            session['username'] = username
            return redirect(url_for("user_area"))
        # if password or username is wrong, return error message
        else:
            error_message = "Your username or password is wrong!"
            return render_template('login.html', error=error_message)
    return render_template('login.html')

# user can create a new username with password
@app.route("/register", methods=["POST"])
def register():

    # get username and password from frontend
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    # check if user exists
    if user:
        return render_template("login.html", error="Username is already used!")
    
    # if not, create a new username with password and safe to db
    else:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = username
        return redirect(url_for('user_area'))
    
# after succesfull login, send user to personal area
@app.route("/user_area")
def user_area():
    if "username" in session:
        return render_template("user_area.html", username=session['username'])
    return redirect(url_for('index'))

# user can logout from session
@app.route("/logout")
def logout():
    session.pop('username',None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    # create all tables if they do not exist yet
    with app.app_context():
        db.create_all()
    app.run()