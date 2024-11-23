from flask import Flask, render_template, request, redirect, url_for, flash
from scraper import run_scraper, get_dates, get_available_dates, get_available_mensas, scraper, url_dict
import os
from config import mail_password,mail_username
from flask_mail import Mail, Message


# Ensure the 'generated_images' folder exists
current_dir = os.path.dirname(os.path.abspath(__file__))
images_folder = os.path.join(current_dir, 'static', 'generated_images')
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

app = Flask(__name__, static_folder='static')

app.secret_key = "your_secret_key" # muss noch als secret versteckt werden


app.config['MAIL_SERVER']= "smtp.gmail.com"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = mail_username
app.config['MAIL_PASSWORD'] = mail_password

mail = Mail(app)

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
                          sender=mail_username,
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

@app.route('/login')
def login():
   return render_template('login.html')

@app.route('/menu_maker')
def menu_maker():
   return render_template('menu_maker.html')

if __name__ == "__main__":
    # hier wird nix verändert
    app.run()