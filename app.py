from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from secret import *
from db.db_write import remove_rating,update_user_vector, setup_database_connection, Dish, Base, User, Course, DishEng, write_to_rating, write_to_user
from db.db_read import get_weekly_recommendation_dict,get_prevornext_weekday_dates,get_average_ratings, get_dishes_of_user,get_weekday_dates,get_week_recommended_dishes,get_cluster_similarity,get_combined_dishes,get_random_dishes,get_user_vector, get_dishes_by_date_location_filtered, get_total_mensas, get_available_mensas, get_first_updated_date, get_dish_count_per_mensa, get_price_development, get_menu_line_distribution, get_average_prices_per_menuline_per_mensa, get_lowest_prices_per_menuline_per_mensa, get_average_prices_per_menuline_per_mensa, get_lowest_prices_per_menuline, get_menu_with_lowest_price, get_meat_options, get_written_forms, get_user_name, get_total_ratings, get_total_menus, get_unique_menu_lines, get_descriptions, get_recipes, get_top_three_mensas, get_top_three_dishes, get_total_ratings_by_user, get_first_rating_date_of_user, get_favorite_mensas_of_user,get_unique_mensas, get_past_6_month_spending, get_current_month_spending
from datetime import datetime, timedelta
import json
from db.utils import compute_cosine_similarity, format_price, format_price_column
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from charts.plotly import top_mensa_for_user_chart,plot_pie_chart,create_weekly_top_dishes_chart,generate_price_chart, create_taste_radarchart, create_past_6_month_spending_chart, plot_average_ratings, create_weekly_rating_plot,create_weekly_top_mensa_chart,plot_rating_histogram
import pandas as pd

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
    user_name = session.get('username')
    mensa_coordinates = {
        "Mensa Morgenstelle": {"top": 30, "left": 16, "text_offset": 0},
        "Cafeteria Morgenstelle": {"top": 30, "left": 16, "text_offset": 30},
        "Mensa Wilhelmstraße": {"top": 47, "left": 49, "text_offset": 0},
        "Cafeteria Wilhelmstraße": {"top": 47, "left": 49, "text_offset": 30},
        "Cafeteria und Mensa Prinz Karl": {"top": 59, "left": 39, "text_offset": 0}
    }
    return render_template('index.html', username=user_name, mensa_coordinates=mensa_coordinates)

@app.route('/navigation')
def navigation():
   lang = session.get('language', 'en')
   session['language'] = lang
   session.permanent = True
   username = session.get('username')  # Get the username from the session
   return render_template('navigation.html', username=username)  # Pass username to the template
                                   
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
                
    return render_template('login.html', username=session.get('username'))

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
        return redirect(url_for('rating'))


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
    return redirect(url_for('index'))


@app.route('/user', methods=['GET','POST'])
def user_page():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    user_name = session.get('username')
    selected_user_type = 'student'


    # if user is not logged in, redirect to login page
    if not user_name:
        return redirect(url_for('login'))
    
    with Session() as db_session:

        # if user is logged in but has not rated dishes yet, redirect to rating page
        user_vector = get_user_vector(user_name, db_session)
        if not user_vector:
            return redirect(url_for('rating'))
        
        if request.method == 'POST':
            menu_id = request.form.get('menu_id')       # if user removes a rating, delete the rating from the database
            selected_user_type = request.form.get('user_type') if request.form.get('user_type') else 'student'  # get student or guest
            remove_rating(menu_id, user_name, engine, Session) if menu_id else None # remove selected rating from Rating Table
            update_user_vector(user_name, engine, db_session) if menu_id else None  # update user vector after rating is removed

            # again check if user_vector exists after rating is removed
            if not user_vector:
                return redirect(url_for('rating'))
        
        # load tables when the page is initialized
        total_ratings = get_total_ratings_by_user(db_session, user_name)
        first_rating_date = get_first_rating_date_of_user(db_session, user_name)
        rated_dishes = get_dishes_of_user(db_session, user_name)
        current_month_spending = get_current_month_spending(db_session, user_name , lang)


        # generate chart to display top mensas for the user
        mensa_user_chart = top_mensa_for_user_chart(db_session, user_name, lang)

        # budget stuff
        past_6_month_spending_chart = create_past_6_month_spending_chart(db_session,user_name, selected_user_type,lang)
        current_spending = current_month_spending[selected_user_type].iloc[0]
        current_spending_formatted = format_price(current_spending)
        current_month = current_month_spending['month_name'].iloc[0]

        # Create tasteprofile radarchart
        cluster_df = get_cluster_similarity(db_session, user_name,lang)
        radar_chart = create_taste_radarchart(cluster_df.iloc[:-3], 'cluster_name', 'scaled')

        # create data to display weekly dish recommendation
        grouped_menu_data = get_weekly_recommendation_dict(db_session, user_name, lang)

        # Create plot for average ratings of all users and user
        average_ratings_plot = plot_average_ratings(db_session, user_name,lang)

        
    return render_template('user.html', 
                           username=user_name, 
                           total_ratings=total_ratings,
                           first_rating_date=first_rating_date,
                           rated_dishes=rated_dishes,
                           mensa_user_chart=mensa_user_chart,
                           radar_chart = radar_chart,
                           average_ratings_plot=average_ratings_plot,
                           dishes=grouped_menu_data,
                           past_6_month_spending_chart = past_6_month_spending_chart,
                           current_spending_formatted = current_spending_formatted,
                           current_month = current_month,
                           user_type = selected_user_type)
                           

@app.route('/rating', methods=['GET','POST'])
def rating():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    on_rating_page = True
    
    with Session() as db_session:
        today = datetime.now().date()
        date = today.strftime('%Y-%m-%d')
        user_name = session.get('username')
        if not user_name:
            return redirect(url_for('login'))

        if request.method == 'POST':
            rating, menu_id = request.form.get('rating'), request.form.get('id')
            print(rating, menu_id)

            # write rating to rating table if user submitted rating
            if rating:
                write_to_rating(menu_id, rating, user_name, on_rating_page, engine, Session)
                if user_name:
                    update_user_vector(user_name, engine, db_session)

        # get random dish that user has not rated before and that is not contained in todays selected
        random_dish = get_random_dishes(datetime.strptime(date, '%Y-%m-%d').date(), lang, user_name, db_session)
        rating_count = get_total_ratings_by_user(db_session, user_name)

        return render_template('rating.html', username=user_name, random_dish=random_dish, rating_count=rating_count)
    


@app.route('/menu', methods=['GET','POST'])
def menu():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    on_rating_page = False

    with Session() as db_session:
        
        # Get additives and allergens 
        additives_dict, additives_dict_eng, allergens_dict, allergens_dict_eng, meats_dict, meats_dict_eng  = get_written_forms(db_session)
 
        # set default values
        mensa_name = request.args.get('selected_mensa', 'all')  # Changed default to 'all'
        today = datetime.now().date()
        available_dates = [(today + timedelta(days=x)).strftime('%Y-%m-%d') for x in range(5)]
        date = today.strftime('%Y-%m-%d')
        available_mensas = get_unique_mensas(db_session)
        selected_diet_meat = 'omnivore'
        selected_price = "studentPrice"
        no_results = False
        recommendation_switch = None
        price_switch = None
        rating_count_switch = None
        rating_switch = None
        

        # if user is logged in, get user_id
        user_name = session.get('username')
        user_vector = get_user_vector(user_name, db_session)

        # if user has not rated dishes yet, redirect to rating page
        #if not user_vector:
        #    return redirect(url_for('rating'))
        print("Before POST check:", recommendation_switch)

        # When user filters, get filtered values
        if request.method == 'POST':
            mensa_name = request.form.get('selected_mensa')
            date_temp = request.form.get('selected_date')
            selected_diet_meat = request.form.getlist('selected_diet_meat')
            selected_price_temp = request.form.get('selected_price')
            recommendation_switch = request.form.get('recommendation_switch')

            price_switch = request.form.get('price_switch')
            rating_switch = request.form.get('rating_switch')
            rating_count_switch = request.form.get('rating_count_switch')

            # get rating from user and selected dish with mensa
            rating, menu_id = request.form.get('rating'), request.form.get('id')
            print(rating, menu_id)

            # write rating and id to database. If user is not logged in, still safe the rating but with NA username
            if rating:
                # write rating to database
                write_to_rating(menu_id, rating, user_name, on_rating_page, engine, Session)

                # update user vector based on new rating if rating is submitted and user is logged in and get new user vector
                if user_name:
                    update_user_vector(user_name, engine, db_session)
                    user_vector = get_user_vector(user_name, db_session)

            # only update the date variable, if a date is selected
            if date_temp:
                date = date_temp
            if selected_price_temp:
                selected_price = selected_price_temp

        
        if user_name:
            random_dish = get_random_dishes(datetime.strptime(date, '%Y-%m-%d').date(),lang,user_name,db_session) # initialize random dish
        else:
            random_dish = (None,None)

        # filter dishes column and merge additional information. Also apply filter of the user directly in the sql query
        dishes = get_dishes_by_date_location_filtered(db_session, datetime.strptime(date, '%Y-%m-%d').date(), mensa_name, selected_diet_meat, session.get('language'))
        
        menu_data = []

        for dish in dishes:
            menu_data.append({
                        'id': dish[0].id,
                        'menu': dish[0].menu,
                        'menuLine': dish[0].menuLine,
                        'studentPrice': dish[0].studentPrice,
                        'guestPrice': dish[0].guestPrice,
                        'studentPrice_formatted': format_price(dish[0].studentPrice),
                        'guestPrice_formatted': format_price(dish[0].guestPrice),
                        'allergens': dish[0].allergens,
                        'additives': dish[0].additives,
                        'location': dish[0].location,
                        'icons':dish[1],
                        'recipe_de':dish[2],
                        'description_de':dish[3],
                        'course':dish[4],
                        'menuLineEng':dish[5],
                        'menuEng':dish[6],
                        'description_en':dish[7],
                        'recipe_en':dish[8],
                        'course_eng':dish[9],
                        'embedding':dish[10],
                        'average_rating':dish[11] or 0, # zero if dish is not rated yet
                        'rating_count':dish[12] or 0, # zero if is not rated yet 
                        'recommendation_score': compute_cosine_similarity(dish[10],user_vector) if user_vector else 0,
                        'is_top_recommendation_in_course': False,  # Initialize to False
                        "studentPrice_imputed": 0 if dish[13] is None else dish[13],
                        "guestPrice_imputed":dish[14],
                        "studentPrice_imputed_formatted":format_price(dish[13]),
                        "guestPrice_imputed_formatted":format_price(dish[14])
                        })
        

        # Implement sorting based on switches
        if recommendation_switch:
            menu_data = sorted(menu_data, key=lambda x: x.get('recommendation_score', 0), reverse=True)
        elif price_switch:
            menu_data = sorted(menu_data, key=lambda x: x['studentPrice'] if x['studentPrice'] != -1 else float(x['studentPrice_imputed']))
        elif rating_switch:
            menu_data = sorted(menu_data, key=lambda x: x.get('average_rating', 0), reverse=True)
        elif rating_count_switch:
            menu_data = sorted(menu_data, key=lambda x: x.get('rating_count', 0), reverse=True)
        
        # Group dishes into a list of dicts with course type as key. e.g. main dish, dessert, site dish
        grouped_menu_data = {}
        for dish in menu_data:
            course_key = dish.get('course') if lang == 'de' else dish.get('course_eng')
            if not course_key:  # Skip if course_key is None or empty
                continue
            if course_key not in grouped_menu_data:
                grouped_menu_data[course_key] = []
            grouped_menu_data[course_key].append(dish)

        # find dish with highest recommendation score for each course type and set flag
        for course_key, dishes in grouped_menu_data.items():
            if dishes:  # Ensure there are dishes for the course
                # Find the dish with the highest recommendation score
                top_dish = max(dishes, key=lambda x: x['recommendation_score'])
                
                # Check if the highest recommendation score is greater than 0
                if top_dish['recommendation_score'] > 0:
                    # Set the flag only for the top dish in the current course
                    for dish in dishes:
                        dish['is_top_recommendation_in_course'] = dish == top_dish
                else:
                    # If the top dish has a score of 0 or less, do not set any flag
                    for dish in dishes:
                        dish['is_top_recommendation_in_course'] = False

        # Check for no results after filtering
        if not grouped_menu_data:
            no_results = True

    return render_template('menu.html', 
                         available_dates=available_dates,
                         available_mensas=available_mensas,
                         dishes=grouped_menu_data,
                         selected_mensa=mensa_name,
                         selected_date=date,
                         selected_price=selected_price,
                         selected_diet_meat=selected_diet_meat,
                         additives_dict=additives_dict,
                         additives_dict_eng=additives_dict_eng,
                         allergens_dict=allergens_dict,
                         allergens_dict_eng=allergens_dict_eng,
                         meats_dict=meats_dict,
                         meats_dict_eng=meats_dict_eng,
                         username=user_name,
                         lang=lang,
                         no_results=no_results,
                         recommendation_switch=recommendation_switch,
                         price_switch=price_switch,
                         rating_switch=rating_switch,
                         rating_count_switch=rating_count_switch,
                         random_dish=random_dish)


@app.route('/analysis')
def analysis():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    username = session.get('username')  

    with Session() as db_session:
        total_mensas = get_total_mensas(db_session)
        total_ratings = get_total_ratings(db_session)
        total_menus = get_total_menus(db_session)
        first_updated_date = get_first_updated_date(db_session)
        week_dates = get_weekday_dates()

        # Create chart to plot avg rating per mensa of the current week
        mensa_plot = create_weekly_top_mensa_chart(db_session, lang, week_dates)

        # Create chart to plot top dishes of the current week
        dish_plot = create_weekly_top_dishes_chart(db_session, lang, week_dates)

        # Create price plot over the whole timeline
        initial_category = "initial"
        initial_price_type = 'studentPrice'
        show_icons_initial = True
        plot_html,categories = generate_price_chart(db_session,initial_category,initial_price_type,show_icons_initial)
        
        # Create average rating plot per week
        week_dates = get_weekday_dates()
        ratings_of_the_week_plot = create_weekly_rating_plot(db_session,week_dates,lang)

        # create pie chart of clusters
        pie_chart = plot_pie_chart(db_session, week_dates,lang)


        return render_template('analysis.html',
                             total_mensas=total_mensas,
                             total_ratings = total_ratings,
                             total_menus = total_menus,
                             first_updated_date=first_updated_date,
                             mensa_plot=mensa_plot,
                             dish_plot=dish_plot,
                             username=username,
                             price_plot=plot_html,
                             categories=categories,
                             selected_category=initial_category,
                             ratings_of_the_week_plot=ratings_of_the_week_plot,
                             week_dates=week_dates,
                             pie_chart=pie_chart)
    
@app.route('/update_price_plot', methods=['POST'])
def update_price_plot():
    """
    This function updates the price plot based on the selected category, price type and icon selection.
    """
    selected_category = request.json.get('category')
    selected_price = request.json.get('price')
    selected_icon = request.json.get('icon')

    selected_icon = {"true": True, "false": False}.get(selected_icon.lower())

    with Session() as db_session:
        plot_html,_ = generate_price_chart(db_session,selected_category,selected_price,selected_icon)

    return jsonify({'plot': plot_html})


@app.route('/update_ratings_plot', methods=['POST'])
def update_ratings_plot():
    """
    This function updates the ratings plot based on the selected week dates.
    """
    lang = session.get('language', 'en')
    direction = request.json.get('direction')
    week_dates = request.json.get('week_dates')
    changed_dates = get_prevornext_weekday_dates(week_dates[0], direction)

    with Session() as db_session:
        ratings_plot = create_weekly_rating_plot(db_session,changed_dates,lang)
        mensa_plot = create_weekly_top_mensa_chart(db_session,lang, changed_dates)
        dish_plot = create_weekly_top_dishes_chart(db_session,lang, changed_dates)
        pie_chart = plot_pie_chart(db_session, changed_dates,lang)

    return jsonify({'ratings_plot':ratings_plot,'week_dates':changed_dates,'mensa_plot':mensa_plot,'dish_plot':dish_plot,'pie_chart':pie_chart})

if __name__ == "__main__":
    with app.app_context():
        Base.metadata.create_all(engine)
    app.run(port=5001)