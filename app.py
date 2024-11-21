from flask import Flask, render_template, request
from scraper import run_scraper, get_dates, get_available_dates, get_available_mensas
import os

# Ensure the 'generated_images' folder exists
current_dir = os.path.dirname(os.path.abspath(__file__))
images_folder = os.path.join(current_dir, 'static', 'generated_images')
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
   return render_template('about.html')

@app.route('/review')
def review():
   return render_template('review.html')

@app.route('/contact')
def contact():
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