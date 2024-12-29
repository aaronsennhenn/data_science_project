from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from werkzeug.security import generate_password_hash, check_password_hash
from secret import *
from db.db_write import update_user_vector, setup_database_connection, Dish, Base, User, Course, DishEng, write_to_rating, write_to_user, write_to_course, write_to_dishes_eng, write_to_directory
from db.db_read import get_dishes_by_date_location, get_dishes_by_date, get_course_eng, get_course, get_next_five_days_data, get_total_mensas, get_available_mensas, get_first_updated_date, get_dish_count_per_mensa, get_price_development, get_menu_line_distribution, get_average_prices_per_menuline_per_mensa, get_lowest_prices_per_menuline_per_mensa, get_average_prices_per_menuline_per_mensa, get_lowest_prices_per_menuline, get_meat_options, get_written_forms, get_user_name, get_total_ratings, get_total_menus, get_unique_menu_lines, get_descriptions, get_recipes
from scraper.data_transform import collect_unique_meats
from datetime import datetime
import plotly
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from db.utils import translate_text_all_capitalized, translate_text_first_word_capitalized
from functools import wraps
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy

current_dir = os.path.dirname(os.path.abspath(__file__))
images_folder = os.path.join(current_dir, 'static', 'generated_images')
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

app = Flask(__name__, static_folder='static')

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/postgres"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = APP_SECRET_KEY

engine, Session = setup_database_connection(USER, PASSWORD, HOST, PORT)

oauth = OAuth(app)      # google login service
db = SQLAlchemy(app)    # database service 
google = oauth.register(
    name='google',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope':'openid profile email'})

@app.route('/set_language/<lang>')
def set_language(lang):
    session['language'] = lang
    session.permanent = True
    return redirect(request.referrer or url_for('index'))

@app.route('/', methods=['GET'])
def index():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    mensa_coordinates = {
        "Mensa Morgenstelle": {"top": 20, "left": 30, "text_offset": 0},
        "Cafeteria Morgenstelle": {"top": 20, "left": 30, "text_offset": 30},
        "Mensa Wilhelmstraße": {"top": 50, "left": 70, "text_offset": 0},
        "Cafeteria Wilhelmstraße": {"top": 50, "left": 70, "text_offset": 30},
        "Cafeteria und Mensa Prinz Karl": {"top": 35, "left": 50, "text_offset": 0}
    }
    return render_template('index.html', mensa_coordinates=mensa_coordinates)


@app.route('/about')
def about():
   lang = session.get('language', 'en')
   session['language'] = lang
   session.permanent = True
   return render_template('about.html')
                                   
# check username and password that user puts into form with db
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with Session() as db_session:
            user = get_user_name(db_session, username)
            
            if user and user.check_password(password):
                session['username'] = username
                return redirect(url_for("menu"))
            else:
                error_message = "Your username or password is wrong!"
                return render_template('login.html', error=error_message)
                
    return render_template('login.html')

@app.route("/register", methods=["POST"])
def register():
    username = request.form['username']
    password = request.form['password']
    
    with Session() as db_session:
        user = get_user_name(db_session, username)
        
        if user:
            return render_template("login.html", error="Username is already used!")
        
        write_to_user(username, password, engine, Session)
        
        session['username'] = username
        return redirect(url_for('menu'))


# login for google
@app.route('/login/google')
def login_google():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    try:
        redirect_url = url_for('authorize_google',_external=True)
        return google.authorize_redirect(redirect_url)
    except Exception as e:
        app.logger.error(f"Error during login:{str(e)}")
        return "Error occurred during login", 500

# authorization form for google
@app.route("/authorize/google")
def authorize_google():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
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

    return redirect(url_for('menu'))

@app.route("/logout")
def logout():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    session.pop('username', None)
    return redirect(url_for('menu'))

@app.route('/menu', methods=['GET','POST'])
def menu():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    with Session() as db_session:
        # Get additives and allergens 
        additives_dict, additives_dict_eng, allergens_dict, allergens_dict_eng, meats_dict, meats_dict_eng  = get_written_forms(db_session)
        
        # Get descriptions and recipes
        descriptions = get_descriptions(db_session)
        recipes = get_recipes(db_session)

        # query available data for the next five days
        data = get_next_five_days_data(db_session)

        # store dates and mensas in a list
        available_dates = sorted([datetime.strptime(key.split(", ")[1], '%Y-%m-%d').strftime('%Y-%m-%d') 
                                for key in data.keys()])
        available_mensas = list(set([mensa for mensas in data.values() for mensa in mensas]))

        # set default values
        mensa_name = request.args.get('selected_mensa', 'all')  # Changed default to 'all'
        date = available_dates[0]
        selected_diet_meat = 'omnivore'
        selected_price = "studentPrice"
        no_results = False 
        headlines_set = set()

        # if user logged in, get user_id
        user_name = session.get('username')

        # When user filters, get filtered values
        if request.method == 'POST':
            mensa_name = request.form.get('selected_mensa')
            date_temp = request.form.get('selected_date')
            selected_diet_meat = request.form.get('selected_diet_meat')
            selected_price = request.form.get('selected_price')

            # get rating from user and selected dish with mensa
            rating, menu_id = request.form.get('rating'), request.form.get('id')

            # write rating and id to database. If user is not logged in, still safe the rating but with NA username
            if rating:
                # write rating to database
                write_to_rating(menu_id, rating, user_name, engine, Session)

                # update user vector based on new rating if rating is submitted and user is logged in 
                if user_name:
                    update_user_vector(user_name, engine, Session)

            # only udate the date variable, if a date is selected
            if date_temp:
                date = date_temp

        # Query dishes based on mensa selection
        if mensa_name == 'all':
            dishes = get_dishes_by_date(db_session, datetime.strptime(date, '%Y-%m-%d').date())
        else:
            dishes = get_dishes_by_date_location(db_session, datetime.strptime(date, '%Y-%m-%d').date(), mensa_name)

        # In the menu() route, modify the menu_data creation:
        menu_data = []
        for dish in dishes:
            # Get the English translations from dishes_eng table
            dish_eng = db_session.query(DishEng).filter(
                DishEng.menuDate == dish.menuDate,
                DishEng.menuEng == translate_text_first_word_capitalized(dish.menu)
            ).first()

            menu_data.append({
            'id': dish.id,
            'menu': dish.menu,
            'menuEng': dish_eng.menuEng if dish_eng else translate_text_first_word_capitalized(dish.menu),
            'menuLine': dish.menuLine,
            'menuLineEng': dish_eng.menuLineEng if dish_eng else translate_text_first_word_capitalized(dish.menuLine),
            'studentPrice': dish.studentPrice,
            'guestPrice': dish.guestPrice,
            'allergens': dish.allergens,
            'additives': dish.additives,
            'meats': dish.meats,
            'icons': dish.icons,
            'location': dish.location,
            'locationEng': dish_eng.locationEng if dish_eng else translate_text_first_word_capitalized(dish.location),
            'course': get_course(db_session, dish.menuDate, dish.menuLine, dish.menu, dish.location),
            'course_eng': get_course_eng(db_session, dish.menuDate, dish.menuLine, dish.menu, dish.location),
            'description_de': descriptions.get(dish.id, {}).get('description_de', ''),
            'description_en': descriptions.get(dish.id, {}).get('description_en', ''),
            'recipe_de': recipes.get(dish.id, {}).get('recipe_de', ''),
            'recipe_en': recipes.get(dish.id, {}).get('recipe_en', '')
        })

        # Group dishes by course_eng
        grouped_menu_data = {}
        for dish in menu_data:
            course_key = dish['course'] if lang == 'de' else dish['course_eng']
            if course_key not in grouped_menu_data:
                grouped_menu_data[course_key] = []
            grouped_menu_data[course_key].append(dish)
        
        # Then filter the grouped dishes based on selected diet or meat
        if selected_diet_meat and 'omnivore' not in selected_diet_meat:
            filtered_grouped_data = {}
            for course, dishes in grouped_menu_data.items():
                filtered_dishes = [dish for dish in dishes if any(icon in dish['icons'] for icon in selected_diet_meat)]
                if filtered_dishes:  # Only include courses that have dishes after filtering
                    filtered_grouped_data[course] = filtered_dishes
            grouped_menu_data = filtered_grouped_data

        # Check for no results after filtering
        if not grouped_menu_data:
            no_results = True

        # encode selected weekday to display
        selected_weekday = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
            
    return render_template('menu.html', 
                         available_dates=available_dates,
                         available_mensas=available_mensas,
                         dishes=grouped_menu_data,
                         selected_mensa=mensa_name,
                         selected_date=date,
                         selected_weekday=selected_weekday,
                         selected_price=selected_price,
                         selected_diet_meat=selected_diet_meat,
                         additives_dict=additives_dict,
                         additives_dict_eng=additives_dict_eng,
                         allergens_dict=allergens_dict,
                         allergens_dict_eng=allergens_dict_eng,
                         meats_dict=meats_dict,
                         meats_dict_eng=meats_dict_eng,
                         descriptions=descriptions,
                         recipes=recipes,
                         username=user_name,
                         lang=lang,
                         no_results=no_results)


@app.route('/analysis')
def analysis():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    with Session() as db_session:
        total_mensas = get_total_mensas(db_session)
        total_ratings = get_total_ratings(db_session)
        total_menus = get_total_menus(db_session)
        names_available_mensas = get_available_mensas(db_session)
        first_updated_date = get_first_updated_date(db_session)
        dish_count_per_mensa = get_dish_count_per_mensa(db_session)
        average_prices = get_average_prices_per_menuline_per_mensa(db_session)  
        lowest_prices = get_lowest_prices_per_menuline(db_session)    
        price_development = get_price_development(db_session)
        menu_line_distribution = get_menu_line_distribution(db_session)
        mensa_average_prices = get_average_prices_per_menuline_per_mensa(db_session)
        mensa_lowest_prices = get_lowest_prices_per_menuline_per_mensa(db_session)

        # Define professional color scheme
        PLOT_COLORS = ['#4F46E5', '#6366F1', '#455d7a']

        fig = make_subplots(
            rows=len(price_development), 
            cols=1,
            subplot_titles=list(price_development.keys()),
            vertical_spacing=0.05
        )

        today = datetime.now().date()

        row = 1
        for menu_line, data in price_development.items():
            for (name, color), price_data in zip(
                [('Pupil Price', PLOT_COLORS[0]), 
                ('Student Price', PLOT_COLORS[1]), 
                ('Guest Price', PLOT_COLORS[2])],
                [data['pupil_prices'], data['student_prices'], data['guest_prices']]
            ):
                fig.add_trace(
                    go.Scatter(
                        x=data['dates'],
                        y=price_data,
                        name=name,
                        line=dict(color=color, width=2),
                        showlegend=(row == 1)
                    ),
                    row=row, col=1
                )
            
            # Add vertical line for today
            fig.add_vline(
                x=today,
                line_width=1,
                line_dash="dash",
                line_color="gray",
                row=row,
                col=1
            )
            row += 1

        fig.update_layout(
        height=400*len(price_development),  # Increased from 300 to 400
        plot_bgcolor='rgb(249, 250, 251)',  # gray-50
        paper_bgcolor='rgba(0,0,0,0)',
        font_family="Inter",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=50, b=50, l=50, r=50)
        )


        fig.update_xaxes(
        gridcolor='rgba(0,0,0,0.1)',
        showline=True,
        linewidth=1,
        linecolor='rgba(0,0,0,0.2)',
        title_text="Date",
        tickformat="%Y-%m-%d",  # Show full date for each tick
        tickangle=45,  # Angle the dates for better readability
        tickmode="auto"
        #ticktext=data['dates'],
        #tickvals=data['dates']
        )

        fig.update_yaxes(
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linewidth=1,
            linecolor='rgba(0,0,0,0.2)',
            dtick=0.5,  # Price increments of 0.50€
            title_text="Price (€)"
        )

        # Create plot_json before using it
        plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        # Create pie charts for each mensa
        VIOLET_COLORS = ['#4F46E5', '#6366F1', '#818CF8', '#A5B4FC', '#233142', '#455d7a', '#e3e3e3']

        pie_charts = {}
        for mensa, distribution in menu_line_distribution.items():
            labels = list(distribution.keys())
            values = list(distribution.values())
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0,
                marker=dict(colors=VIOLET_COLORS),
                textinfo='label+percent',
                textposition='inside',
                insidetextorientation='horizontal',
                textfont=dict(size=10, color='white', family='Inter'),
                hovertemplate="%{value} dishes<extra></extra>"
            )])
            
            fig.update_layout(
                showlegend=False,
                margin=dict(t=0, b=0, l=0, r=0),
                height=200,  # Reduced size
                width=200,   # Reduced size
                paper_bgcolor='rgba(0,0,0,0)',
                font_family='Inter'
            )
            
            pie_charts[mensa] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


        # Add pie_charts to the template context
        return render_template('analysis.html',
                             total_mensas=total_mensas,
                             total_ratings = total_ratings,
                             total_menus = total_menus,
                             names_available_mensas=names_available_mensas,
                             first_updated_date=first_updated_date,
                             dish_count_per_mensa=dish_count_per_mensa,
                             mensa_average_prices=mensa_average_prices,
                             mensa_lowest_prices=mensa_lowest_prices,
                             average_prices=average_prices,           
                             lowest_prices=lowest_prices,   
                             plot_json=plot_json,
                             pie_charts=pie_charts)

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
    
    with Session() as db_session:
        dishes = get_dishes_by_date_location(db_session, datetime.strptime(date, '%Y-%m-%d').date(), mensa_name)
        
        menu_data = []
        for dish in dishes:
            menu_data.append({
                'menu': dish.menu,
                'studentPrice': dish.studentPrice,
                'guestPrice': dish.guestPrice,
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
        #write_to_course(engine, Session)  #not needed to be rerunned
        #write_to_directory(engine, Session) #need to be rerunned if more data in dishes is available
        #write_to_dishes_eng(engine, Session)  #need to be rerunned if more data in dishes is available
    app.run()