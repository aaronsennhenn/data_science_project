from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from scraper import run_scraper, get_dates, get_available_dates, get_available_mensas, scraper, url_dict
import os
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from secret import *
from authlib.integrations.flask_client import OAuth
from archive.scraper_daniel import get_test_dict, get_scraper_df


# Ensure the 'generated_images' folder exists
current_dir = os.path.dirname(os.path.abspath(__file__))
images_folder = os.path.join(current_dir, 'static', 'generated_images')
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

app = Flask(__name__, static_folder='static')


################################# app systems variables #######################################

# contact us mail 
app.config['MAIL_SERVER']= "smtp.gmail.com"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD

# postgressql database
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/postgres"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# app secret for session
app.secret_key = APP_SECRET_KEY

################################# initialize app services #######################################

mail = Mail(app)        # contact us service
db = SQLAlchemy(app)    # database service
oauth = OAuth(app)      # google login service


################################# google authentification #######################################

google = oauth.register(
    name='google',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope':'openid profile email'})

################################# app routes #######################################


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

@app.route('/dining_facilities', methods=['GET', 'POST'])
def dining_facilities():
   # Days of the week
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Sample data structure
    overview_data = get_test_dict()

    #return "Welcome to the weekly menu!"
    return render_template('weekly_menu.html', overview_data=overview_data,days=days,zip=zip)

@app.route('/dish-clicked', methods=['POST'])
def dish_clicked():
    try:
        mensa_name = request.form.get('mensa_name')  # Extract restaurant name
        mensa_day = request.form.get('mensa_day')  # Extract weekday
        if not mensa_name or not mensa_day:
            return jsonify({'error': 'Missing data'}), 400
    # Do something with the data (e.g., log, process)
        print(f"Received data: {mensa_name}, {mensa_day}")
        #return jsonify({'success': True, 'message': 'Data received'})  # Send back a valid JSON response
        #return redirect(url_for('mensa_menu', selected_mensa=mensa_name, selected_date=mensa_date))
        return jsonify({'success': True, 'message': 'Data received'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/mensa_menu')
def mensa_menu():
    mensa_name = request.args.get('mensa_name')  # Get the selected mensa name
    mensa_day = request.args.get('mensa_day')    # Get the selected weekday
    
    # Debugging: Print the values to check if they are correct
    print(f"Selected Mensa: {mensa_name}, Selected day: {mensa_day}")
    
    if not mensa_name or not mensa_day:
        return "Error: Missing data", 400
    

    # filter df based on mensa_name and mensa_day
    filtered_df = get_scraper_df(mensa_name,mensa_day)

    # render to html for testing
    df_html = filtered_df.to_html(classes='table table-bordered table-striped', index=False)


    # Render the mensa_result.html template with the passed data
    return render_template('mensa_result.html', mensa_name=mensa_name, mensa_day=mensa_day, table=df_html)

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
    username = db.Column(db.String(50), unique=True, nullable=False)
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
        db.session.close()

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

# login for google
@app.route('/login/google')
def login_google():
    try:
        redirect_url = url_for('authorize_google',_external=True)
        return google.authorize_redirect(redirect_url)
    except Exception as e:
        app.logger.error(f"Error during login:{str(e)}")
        return "Error occurred during login", 500
    
# authorization form for google
@app.route("/authorize/google")
def authorize_google():
    token = google.authorize_access_token()
    userinfo_endpoint = google.server_metadata['userinfo_endpoint']
    resp = google.get(userinfo_endpoint)
    user_info = resp.json()
    username = user_info['email']

    # create new user in db
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)
        db.session.commit()
        db.session.close()

    session['username'] = username
    session['oauth_token'] = token

    return redirect(url_for('user_area'))



if __name__ == "__main__":
    # create all tables if they do not exist yet
    with app.app_context():
        db.create_all()
    app.run()