from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from werkzeug.security import generate_password_hash, check_password_hash
from secret import *
from db.db_write import setup_database_connection, Dish, Base
from db.db_read import get_user_by_username, get_dishes_by_date_location, get_all_dishes, get_image_path, get_next_five_days_data

from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
images_folder = os.path.join(current_dir, 'static', 'generated_images')
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

app = Flask(__name__, static_folder='static')

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/postgres"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = APP_SECRET_KEY

engine, Session = setup_database_connection(USER, PASSWORD, HOST, PORT)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
   return render_template('about.html')

@app.route('/review')
def review():
   return render_template('review.html')

@app.route('/dining_facilities', methods=['GET'])
def dining_facilities():
    with Session() as session:
        data = get_next_five_days_data(session)
        available_dates = list(data.keys())
        available_mensas = list(set([mensa for mensas in data.values() for mensa in mensas]))
        
    return render_template('dining_facilities.html', 
                         available_dates=available_dates,
                         available_mensas=available_mensas)


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


@app.route('/mensa/<mensa_name>')
def mensa_menu(mensa_name):
    date = request.args.get('date')
    
    with Session() as session:
        dishes = get_dishes_by_date_location(session, datetime.strptime(date, '%Y-%m-%d').date(), mensa_name)
        
        menu_data = []
        for dish in dishes:
            menu_data.append({
                'menuGer': dish.menuGer,
                'menuEng': dish.menuEng,
                'studentPrice': dish.studentPrice,
                'guestPrice': dish.guestPrice,
                'image_path': dish.image_path,
                'allergens': dish.allergens,
                'additives': dish.additives
            })
            
        return render_template('mensa_result.html',
                             mensa_name=mensa_name,
                             mensa_day=date,
                             dishes=menu_data)

@app.route('/check_image/<filename>')
def check_image(filename):
    image_path = os.path.join(images_folder, filename)
    if os.path.exists(image_path):
        return '', 200
    else:
        return '', 404

if __name__ == "__main__":
    with app.app_context():
        Base.metadata.create_all(engine)
    app.run()