from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from werkzeug.security import generate_password_hash, check_password_hash
from secret import *
from db.db_write import setup_database_connection, Dish, Base,write_to_rating
from db.db_read import get_user_by_username, get_dishes_by_date_location, get_all_dishes, get_image_path, get_next_five_days_data, get_total_mensas, get_available_mensas, get_first_updated_date, get_dish_count_per_mensa, get_price_development, get_menu_line_distribution, get_average_prices_per_menuline_per_mensa, get_lowest_prices_per_menuline_per_mensa, get_average_prices_per_menuline_per_mensa, get_lowest_prices_per_menuline, get_meat_options
from scraper.data_transform import collect_unique_meats
from datetime import datetime
import plotly
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

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

@app.route('/dining_facilities', methods=['GET','POST'])
def dining_facilities():
    with Session() as session:

        # query available data for the next five days
        data = get_next_five_days_data(session)

        # store dates and mensas in a list
        available_dates = [key.split(", ")[1] for key in data.keys()]
        available_mensas = list(set([mensa for mensas in data.values() for mensa in mensas]))

        # get available meat options
        available_meat = get_meat_options(session)
        available_meat = collect_unique_meats(available_meat)

        # display default mensa and date when loading the page for the first time
        mensa_name = available_mensas[0]
        date = available_dates[0]

        # set default values for filters
        selected_meat = None
        selected_diet = None
        rating = None
        selected_price = "studentPrice"


        # When user filters, get filtered mensa and date values
        if request.method == 'POST':
            mensa_name = request.form.get('selected_mensa')
            date = request.form.get('selected_date')
            selected_meat = request.form.get('selected_meat')
            selected_diet = request.form.get('selected_diet')
            selected_price = request.form.get('selected_price')

            # get rating from user and selected dish with mensa
            rating,id = request.form.get('rating'),request.form.get('id')

            # write rating and id to database
            if rating:
                write_to_rating(id,rating,engine,Session)

            # if no date is selected, set default date to today
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')


        # Query dishes for respective mensa and date
        dishes = get_dishes_by_date_location(session, datetime.strptime(date, '%Y-%m-%d').date(), mensa_name)
        menu_data = []
        for dish in dishes:
            menu_data.append({
                'id': dish.id,
                'menu': dish.menu,
                'studentPrice': dish.studentPrice,
                'guestPrice': dish.guestPrice,
                'allergens': dish.allergens,
                'additives': dish.additives,
                'menuLine': dish.menuLine,
                'meats': dish.meats,
                'icons': dish.icons
            })
        
        # if user filters by meat, diet or price, filter the dishes
        if selected_meat:
            menu_data = [dish for dish in menu_data if selected_meat.lower() in dish['meats'].lower()]
        
        if selected_diet:
            menu_data = [dish for dish in menu_data if selected_diet.lower() in dish['icons'].lower()]

        # encode selected weekday to display
        selected_weekday = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
            
    return render_template('dining_facilities.html', 
                         available_dates=available_dates,
                         available_mensas=available_mensas,
                         available_meat=available_meat,
                         dishes=menu_data,
                         selected_mensa=mensa_name,
                         selected_date=date,
                         selected_weekday=selected_weekday,
                         selected_price=selected_price)

@app.route('/analysis')
def analysis():
    with Session() as session:
        total_mensas = get_total_mensas(session)
        names_available_mensas = get_available_mensas(session)
        first_updated_date = get_first_updated_date(session)
        dish_count_per_mensa = get_dish_count_per_mensa(session)
        average_prices = get_average_prices_per_menuline_per_mensa(session)  
        lowest_prices = get_lowest_prices_per_menuline(session)    
        price_development = get_price_development(session)
        menu_line_distribution = get_menu_line_distribution(session)
        mensa_average_prices = get_average_prices_per_menuline_per_mensa(session)
        mensa_lowest_prices = get_lowest_prices_per_menuline_per_mensa(session)

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
        dtick="M1",  # Monthly ticks
        title_text="Date",
        tickformat="%Y-%m-%d",  # Show full date for each tick
        tickangle=45,  # Angle the dates for better readability
        tickmode="array",
        ticktext=data['dates'],
        tickvals=data['dates']
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
    
    with Session() as session:
        dishes = get_dishes_by_date_location(session, datetime.strptime(date, '%Y-%m-%d').date(), mensa_name)
        
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
    app.run(debug=True)