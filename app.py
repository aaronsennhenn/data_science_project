from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from secret import *
from db.db_write import update_user_vector, setup_database_connection, Dish, Base, User, Course, DishEng, write_to_rating, write_to_user
from db.db_read import get_cluster_similarity,get_combined_dishes,get_random_dishes,get_user_vector, get_dishes_by_date_location_filtered, get_total_mensas, get_available_mensas, get_first_updated_date, get_dish_count_per_mensa, get_price_development, get_menu_line_distribution, get_average_prices_per_menuline_per_mensa, get_lowest_prices_per_menuline_per_mensa, get_average_prices_per_menuline_per_mensa, get_lowest_prices_per_menuline, get_menu_with_lowest_price, get_meat_options, get_written_forms, get_user_name, get_total_ratings, get_total_menus, get_unique_menu_lines, get_descriptions, get_recipes, get_top_three_mensas, get_top_three_dishes, get_total_ratings_by_user, get_first_rating_date_of_user, get_favorite_dishes_of_user, get_favorite_mensas_of_user,get_unique_mensas, compute_tasteprofile_similiarity_by_uservector
from scraper.data_transform import collect_unique_meats
from datetime import datetime, timedelta
import plotly
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
import json
from db.utils import compute_cosine_similarity
from functools import wraps
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from charts.plotly import generate_price_chart, create_taste_radarchart

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
        "Mensa Morgenstelle": {"top": 20, "left": 30, "text_offset": 0},
        "Cafeteria Morgenstelle": {"top": 20, "left": 30, "text_offset": 30},
        "Mensa Wilhelmstraße": {"top": 50, "left": 70, "text_offset": 0},
        "Cafeteria Wilhelmstraße": {"top": 50, "left": 70, "text_offset": 30},
        "Cafeteria und Mensa Prinz Karl": {"top": 35, "left": 50, "text_offset": 0}
    }
    return render_template('index.html', username=user_name, mensa_coordinates=mensa_coordinates)

@app.route('/about')
def about():
   lang = session.get('language', 'en')
   session['language'] = lang
   session.permanent = True
   username = session.get('username')  # Get the username from the session
   return render_template('about.html', username=username)  # Pass username to the template
                                   
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
    return redirect(url_for('index'))


@app.route('/user')
def user_page():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    user_name = session.get('username')
    if not user_name:
        return redirect(url_for('login'))

    db_session = Session()
    try:
        total_ratings = get_total_ratings_by_user(db_session, user_name)
        first_rating_date = get_first_rating_date_of_user(db_session, user_name)
        favorite_dishes = get_favorite_dishes_of_user(db_session, user_name, lang)
        favorite_mensas = get_favorite_mensas_of_user(db_session, user_name, lang)
        tasteprofile_df = compute_tasteprofile_similiarity_by_uservector(db_session, user_name)

        # Create top mensas chart
        mensa_trace = {
            'x': [mensa[0] for mensa in favorite_mensas],
            'y': [mensa[1] for mensa in favorite_mensas],
            'type': 'bar',
            'marker': {
                'color': ['#4F46E5', '#6366F1', '#818CF8']
            }
        }
        mensa_layout = {
            'xaxis': {'title': 'Mensa', 'tickangle': 45},
            'yaxis': {'title': 'Durchschnittliche Bewertung' if lang == 'de' else 'Average Rating'}
        }
        mensa_user_chart = json.dumps({'data': [mensa_trace], 'layout': mensa_layout}, cls=plotly.utils.PlotlyJSONEncoder)

        # Create top dishes chart
        dish_trace = {
            'x': [dish[0] for dish in favorite_dishes],
            'y': [dish[1] for dish in favorite_dishes],
            'type': 'bar',
            'marker': {
                'color': ['#4F46E5', '#6366F1', '#818CF8']
            }
        }
        dish_layout = {
            'xaxis': {'title': 'Menü' if lang == 'de' else 'Dish', 'tickangle': 45},
            'yaxis': {'title': 'Bewertung' if lang == 'de' else 'Rating'}
        }
        dish_user_chart = json.dumps({'data': [dish_trace], 'layout': dish_layout}, cls=plotly.utils.PlotlyJSONEncoder)
        
        
                # get cosine similarity of user vector
        cluster_df = get_cluster_similarity(db_session, user_name)

        #Create tasteprofile radarchart
        country_chart = create_taste_radarchart(cluster_df.iloc[:-3], 'cluster_name', 'scaled')
        regional_chart = create_taste_radarchart(cluster_df.iloc[-3:], 'cluster_name', 'scaled')

    finally:
        db_session.close()

    return render_template('user.html', 
                           username=user_name, 
                           total_ratings=total_ratings,
                           first_rating_date=first_rating_date,
                           favorite_dishes=favorite_dishes,
                           favorite_mensas=favorite_mensas,
                           mensa_user_chart=mensa_user_chart,
                           dish_user_chart=dish_user_chart,
                           country_chart = country_chart,
                           regional_chart=regional_chart)


@app.route('/menu', methods=['GET','POST'])
def menu():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    with Session() as db_session:
        
        # Get additives and allergens 
        additives_dict, additives_dict_eng, allergens_dict, allergens_dict_eng, meats_dict, meats_dict_eng  = get_written_forms(db_session)
 
        # set default values
        mensa_name = 'all'  # Changed default to 'all' to show dishes of all mensas
        today = datetime.now().date()
        available_dates = [(today + timedelta(days=x)).strftime('%Y-%m-%d') for x in range(5)]
        date = today.strftime('%Y-%m-%d')
        available_mensas = get_unique_mensas(db_session)
        selected_diet_meat = 'omnivore'
        selected_price = "studentPrice"
        no_results = False
        recommendation_switch = None

        # if user is logged in, get user_id
        user_name = session.get('username')
        user_vector = get_user_vector(user_name, db_session)



        # When user filters, get filtered values
        if request.method == 'POST':
            mensa_name = request.form.get('selected_mensa')
            date_temp = request.form.get('selected_date')
            selected_diet_meat = request.form.getlist('selected_diet_meat')
            selected_price = request.form.get('selected_price')
            recommendation_switch = request.form.get('recommendation_switch')

            # get rating from user and selected dish with mensa
            rating, menu_id = request.form.get('rating'), request.form.get('id')
            print(rating, menu_id)

            # write rating and id to database. If user is not logged in, still safe the rating but with NA username
            if rating:
                # write rating to database
                write_to_rating(menu_id, rating, user_name, engine, Session)

                # update user vector based on new rating if rating is submitted and user is logged in and get new user vector
                if user_name:
                    update_user_vector(user_name, engine, Session)
                    user_vector = get_user_vector(user_name, db_session)

            # only update the date variable, if a date is selected
            if date_temp:
                date = date_temp

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
                        'allergens': dish[0].allergens,
                        'additives': dish[0].additives,
                        'location': dish[0].location,
                        'icons':dish[1],
                        'receipe_de':dish[2],
                        'description_de':dish[3],
                        'course':dish[4],
                        'menuLineEng':dish[5],
                        'menuEng':dish[6],
                        'description_en':dish[7],
                        'recipe_en':dish[8],
                        'course_eng':dish[9],
                        'embedding':dish[10],
                        'average_rating':dish[11],
                        'rating_count':dish[12],
                        'recommendation_score': compute_cosine_similarity(dish[10],user_vector) if user_vector else 0,
                        'is_top_recommendation_in_course': False  # Initialize to False
                        })
        
        # Sort dishes by recommendation score if recommendation switch is on
        if recommendation_switch:
            menu_data = sorted(menu_data, key=lambda x: x['recommendation_score'], reverse=True)
        

        # Group dishes into a list of dicts with course type as key. e.g. main dish, dessert, site dish
        grouped_menu_data = {}
        for dish in menu_data:
            course_key = dish.get('course') if lang == 'de' else dish.get('course_eng')
            if not course_key:  # Skip if course_key is None or empty
                continue
            if course_key not in grouped_menu_data:
                grouped_menu_data[course_key] = []
            grouped_menu_data[course_key].append(dish)

        # find dish with highest recommendation score for course type and set flag
        target_course_keys = 'Hauptspeise' if lang == 'de' else 'Main Dish'
        for course_key, dishes in grouped_menu_data.items():
            if course_key in target_course_keys:
                # Find the dish with the highest recommendation score
                top_dish = max(dishes, key=lambda x: x['recommendation_score'])
                
                # Set the flag only for the top dish in the target courses
                for dish in dishes:
                    dish['is_top_recommendation_in_course'] = dish == top_dish

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
                         random_dish=random_dish)


@app.route('/analysis')
def analysis():
    lang = session.get('language', 'en')
    session['language'] = lang
    session.permanent = True
    username = session.get('username')  # Get the username from the session
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
        top_three_mensas = get_top_three_mensas(db_session)
        top_three_dishes = get_top_three_dishes(db_session)
        menus_with_lowest_price = get_menu_with_lowest_price(db_session)

        # Define professional color scheme
        lang = session.get('language', 'en')
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

        # Create top mensas chart
        mensa_trace = {
            'x': [item['location'] for item in top_three_mensas],
            'y': [item['avg_rating'] for item in top_three_mensas],
            'type': 'bar',
            'marker': {
                'color': ['#4F46E5', '#6366F1', '#818CF8']
            }
        }
        mensa_layout = {
            #'title': 'Top 3' if lang == 'de' else 'Top 3',
            'xaxis': {'title': 'Mensa', 'tickangle': 0},
            'yaxis': {'title': 'Durchschnittliche Bewertung' if lang == 'de' else 'Average Rating'}
        }
        mensa_chart = json.dumps({'data': [mensa_trace], 'layout': mensa_layout}, cls=plotly.utils.PlotlyJSONEncoder)

        # Create top dishes chart
        dish_trace = {
            'x': [item['dish_name'] for item in top_three_dishes],
            'y': [item['avg_rating'] for item in top_three_dishes],
            'type': 'bar',
            'marker': {
                'color': ['#4F46E5', '#6366F1', '#818CF8']
            }
        }
        dish_layout = {
            #'title': 'Top 3' if lang == 'de' else 'Top 3',
            'xaxis': {'title': 'Menü' if lang == 'de' else 'Dish', 'tickangle': 45},
            'yaxis': {'title': 'Durchschnittliche Bewertung' if lang == 'de' else 'Average Rating'}
        }
        dish_chart = json.dumps({'data': [dish_trace], 'layout': dish_layout}, cls=plotly.utils.PlotlyJSONEncoder)


        ### Price Chart ###

        # get 
        initial_category = "initial"
        initial_price_type = 'guestPrice'
        show_icons_initial = True

        plot_html,categories = generate_price_chart(db_session,initial_category,initial_price_type,show_icons_initial)


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
                             pie_charts=pie_charts,
                             top_three_mensas=top_three_mensas,
                             top_three_dishes=top_three_dishes,
                             mensa_chart=mensa_chart,
                             dish_chart=dish_chart,
                             menus_with_lowest_price=menus_with_lowest_price,
                             username=username,
                             price_plot=plot_html,
                             categories=categories,
                             selected_category=initial_category)
    
# Route to update the plot dynamically
@app.route('/update_plot', methods=['POST'])
def update_plot():

    selected_category = request.json.get('category')
    selected_price = request.json.get('price')
    selected_icon = request.json.get('icon')

    selected_icon = {"true": True, "false": False}.get(selected_icon.lower())


    print(selected_category, selected_price, selected_icon)

    with Session() as db_session:
        plot_html,_ = generate_price_chart(db_session,selected_category,selected_price,selected_icon)


    return jsonify({'plot': plot_html})



if __name__ == "__main__":
    with app.app_context():
        Base.metadata.create_all(engine)
    app.run()