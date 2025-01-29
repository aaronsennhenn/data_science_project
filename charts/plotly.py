from flask import request
import plotly.graph_objects as go
import plotly.io as pio
from plotly.colors import sequential
from db.db_read import get_combined_dishes,get_ratings_of_the_week,get_top_three_mensas,get_top_three_dishes,get_dishes_and_rating_by_week,get_cluster_similarity_for_week,get_favorite_mensas_of_user,get_past_6_month_spending,get_average_ratings
import pandas as pd
from datetime import datetime
import json
"""
In this script, all functions are included that generat our plotly charts.

"""

# Define the colors
colors = ['#4F46E5', '#6366F1', '#818CF8']

def format_labels(labels: list) -> list:
    """
    Formats a list of labels by inserting a line break ("<br>") every n words in each label.

    Args:
        labels (list of str): A list of labels (strings) to be formatted.

    Returns:
        list of str: A list of formatted labels with "<br>" tags inserted.
    """
    def insert_br_every_n_words(label, n=3):
        words = label.split()
        return '<br>'.join([' '.join(words[i:i+n]) for i in range(0, len(words), n)])
    return [insert_br_every_n_words(label) for label in labels]

def format_labels_mensas(labels: list) -> list:
    """
    Formats a list of labels specific to mensas by inserting a line break ("<br>") every n words in each label.

    Args:
        labels (list of str): A list of labels (strings) to be formatted, typically representing menu items or categories.

    Returns:
        list of str: A list of formatted labels with "<br>" tags inserted every n words.
    """
    def insert_br_every_n_words(label, n=3):
        words = label.split()
        return '<br>'.join([' '.join(words[i:i+n]) for i in range(0, len(words), n)])
    return [insert_br_every_n_words(label) for label in labels]

def generate_price_chart(db_session, selected_category, selected_price_type, show_icons,lang):
    """
    Generates an interactive price chart for menu items using Plotly, based on the selected category 
    and price type. Optionally includes icons as a grouping factor.

    Args:
        db_session (Session): The database session used to retrieve data.
        selected_category (str): The selected menu category for filtering the data. 
                                 Use "initial" to default to the first available category.
        selected_price_type (str): The type of price to display on the chart 
                                   (e.g., "studentPrice", "guestPrice").
        show_icons (bool): A toggle to include icons as a grouping factor in the chart. 
                           If True, data points will be grouped by icons.

    Returns:
        tuple: A tuple containing:
            - plot_html (str): The HTML representation of the Plotly figure.
            - unique_categories (list): A list of unique menu categories available in the data.
    """
        
    # Get data
    df = get_combined_dishes(db_session)

    df = df[(df["studentPrice"] > 0) & (df["guestPrice"] > 0) & (df["icons_clean"] != "nan")]

    menuLine_translation_dict = {"Auswahlgericht":"Selection Dish",
                                 "Beilagen vorport.":"Side Dishes preportioned",
                                 "Tagesmenü vegetarisch":"Vegetarian Daily Menu",
                                 "Tagesmenü vegan":"Vegan Daily Menu",
                                 "Tagesmenü":"Daily Menu",
                                 "Auswahlgericht vegan":"Vegan Selection Dish",
                                 "Dessert vorport.":"Dessert preportioned",
                                 "Angebot d. Tages vegan":"Vegan Offer Of the Day",
                                 "Salat-/ Gemüsebuffet 100g":"Salad/Vegetable Buffet 100g",
                                 "Auswahlgericht veget.":"Vegetarian Selection Dish",
                                 "Angebot des Tages":"Offer Of The Day",
                                 "mensaVital vegan":"MensaVital Vegan",
                                 "Beilagen SB":"Side Dishes Self-Service",
                                 "Dessert SB":"Dessert Self-Service",
                                 "Angebot d. Tages veget.":"Vegetarian Offer Of the Day",
                                 "mensaVital":"MensaVital",
                                 "mensaVital vegetarisch":"MensaVital Vegetarian",
                                 "Aktionsmenü":"Special Menu"}
    
    if lang == 'en':
        df['menuLine'] = df['menuLine'].map(menuLine_translation_dict)


    # Default initial values
    if selected_category == "initial":
        selected_category = df['menuLine'].unique()[0]

    # Filter the DataFrame
    filtered_df = df[df['menuLine'] == selected_category]

    # Define the colors
    PLOT_COLORS = sequential.Viridis
    

    # Create the Plotly figure
    fig = go.Figure()

    # Add traces based on the toggle state
    if show_icons:
        unique_icons = filtered_df['icons_clean'].unique()
        for i, icon in enumerate(unique_icons):
            icon_data = filtered_df[filtered_df['icons_clean'] == icon]
            icon_data['hover_text'] = (
                "Menu: " + icon_data['menu']
            )
            fig.add_scatter(
                x=icon_data['menuDate'],
                y=icon_data[selected_price_type],
                mode='markers',
                name=f'{icon}',
                marker=dict(color=PLOT_COLORS[i % len(PLOT_COLORS)]),
                text=icon_data['hover_text'],
                hovertemplate=(
                    '<b>Date:</b> %{x}<br>'+
                    '<b>Price:</b> %{y}<br>'+
                    '%{text}<extra></extra>'
                )
        )
    
    else:
        filtered_df['hover_text'] = (
                "Menu: " + filtered_df['menu']
            )
        fig.add_scatter(
            x=filtered_df['menuDate'],
            y=filtered_df[selected_price_type],
            mode='markers',
            name='All Prices',
            text=filtered_df['hover_text'],
            hovertemplate=(
                '<b>Date:</b> %{x}<br>'+
                '<b>Price:</b> %{y}<br>'+
                '%{text}<extra></extra>'
            )
        )

    # Update layout
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title=selected_price_type.capitalize(),
        legend=dict(
            orientation='h',  
            yanchor='bottom',   
            y=1.02,           
            xanchor='center',
            x=0.5   
        )
    )

    # Convert the Plotly figure to HTML
    plot_html = pio.to_html(fig, full_html=False)

    return plot_html,df['menuLine'].unique()

def create_taste_radarchart(df, taste_label, similarity):
    """
    Creates a radar chart to visualize the relationship between taste attributes and their similarity values.

    Args:
        df (pd.DataFrame): The dataframe containing the data for the radar chart.
        taste_label (str): The column name representing the taste labels.
        similarity (str): The column name representing the similarity values corresponding to the taste labels.

    Returns:
        str: The HTML representation of the radar chart that can be embedded in web pages or reports.
    """

    r = df[similarity].tolist()  
    theta = df[taste_label].tolist()  

    #Create Radar Chart
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=r, 
        theta=theta, 
        fill='toself',  
        marker=dict(color=colors[0]),
        name = None
    ))

    #Update layout for better appearance
    fig.update_layout(
        autosize=True,
        polar=dict(
            radialaxis=dict(
                visible=False,
                range=[0, 1]
            )
        ),
        showlegend=False,
        height = 500,
        width = 500
    )

    # Convert figure to html format
    fig_html = pio.to_html(fig, full_html=False)
    
    return fig_html

def plot_average_ratings(db_session,user_name,lang):
    """
    Plots a bar chart comparing the average ratings of a specified user against all other users
    across different categories, with support for multilingual display (English and German).

    Args:
        db_session (Session): The database session used to retrieve data.
        user_name (str): The name of the user for whom the ratings are being displayed.
        lang (str): The language in which the chart labels should be displayed.

    Returns:
        str: The HTML representation of the Plotly bar chart, which can be embedded in web pages.
    """

    # translate categores.
    translation_dict = {
        'vegan': 'Vegan',
        'beef': 'Rindfleisch',
        'pork': 'Schwein',
        'vegetarian': 'Vegetarisch',
        'poultry': 'Geflügel',
        'fish': 'Fisch',
        'mensaVital': 'MensaVital',
        'nan': 'Andere'  
    }

    # get rating data of user and all other users
    user_ratings = get_average_ratings(db_session,user_name)
    all_ratings = get_average_ratings(db_session)

    if lang == 'de':
        user_ratings = {translation_dict.get(key, key): value for key, value in user_ratings.items()}
        all_ratings = {translation_dict.get(key, key): value for key, value in all_ratings.items()}
    else:
        # replace nan icon value with "others"
        user_ratings = {('others' if key == 'nan' else key): value for key, value in user_ratings.items()}
        all_ratings = {('others' if key == 'nan' else key): value for key, value in all_ratings.items()}



    categories = sorted(set(user_ratings.keys()).union(all_ratings.keys()))
    user_values = [user_ratings.get(category, 0) for category in categories]
    all_values = [all_ratings.get(category, 0) for category in categories]

    formatted_categories = format_labels(categories)

    fig = go.Figure()

    # Add user ratings to the bar chart
    fig.add_trace(go.Bar(
        x=formatted_categories,
        y=user_values,
        name="Your Ratings" if lang == 'en' else "Deine Bewertungen",
        marker=dict(color=colors[1])
    ))

    # Add all users' ratings to the bar chart with transparency
    fig.add_trace(go.Bar(
        x=formatted_categories,
        y=all_values,
        name="Other Users' Ratings" if lang == 'en' else "Bewertungen anderer Nutzer",
        marker=dict(color=colors[2]),
        opacity=0.5
    ))

    # Update layout for better visualization
    fig.update_layout(
        xaxis={
        'title': {
            'text': 'Categories' if lang == 'en' else 'Kategorien',
            'standoff': 20  
        },
        'tickangle': -45,
        'automargin': True  
        },
        yaxis={
            'title': 'Average Rating' if lang == 'en' else 'Durchschnittliche Bewertung'
        },
        barmode="group",
        xaxis_tickangle=-45,
        legend=dict(
            orientation="h",  # Set the orientation to horizontal
            yanchor="bottom",
            y=1.02,  # Position the legend above the plot
            xanchor="center",
            x=0.5
        ),
        height = 400,
        width = 500
    )

    fig_html = pio.to_html(fig, full_html=False)
    return fig_html


def create_past_6_month_spending_chart(db_session, user_name, user_type, lang):
    """
    Creates a bar chart displaying the user's spending over the past 6 months. The chart
    is color-coded, with the last month's spending highlighted.

    Args:
        db_session (Session): The database session used to retrieve data.
        user_name (str): The name of the user for whom the chart is generated.
        user_type (str): The type of spending to display (e.g., 'studentPrice', 'guestPrice').
        lang (str): The language in which the month names should be displayed ('en' for English, 'de' for German).

    Returns:
        str: The HTML representation of the Plotly bar chart, which can be embedded in web pages.
    """

    df = get_past_6_month_spending(db_session, user_name, lang)

    # Get months and spending data from the DataFrame and reverse the order
    months = df['month_name'].tolist()[::-1]  
    spending = df[user_type].tolist()[::-1] 
    
    # Highlight the last item (current month) in yellow
    colors = ['#6366F1'] * len(spending)
    colors[-1] = '#6366F1'
    
    # Create the bar plot
    fig = go.Figure()

    # Add the spending data as a bar plot
    fig.add_trace(go.Bar(
        x=months,
        y=spending,
        name='Spending',
        marker=dict(color=colors)
    ))

    # Add title and labels
    fig.update_layout(
        showlegend=False,
        height=300,
        plot_bgcolor='white',  
        paper_bgcolor='white',
        xaxis=dict(
            tickangle=-45  
        ),
        yaxis=dict(
            showgrid=True,  # Enable grid lines on the x-axis
            gridcolor='lightgray',  # Set grid line color
    ))
    
    # Convert the figure to HTML and return it
    fig_html = pio.to_html(fig, full_html=False)

    return fig_html

day_translation_dict = {'Monday': 'Montag','Tuesday': 'Dienstag','Wednesday': 'Mittwoch','Thursday': 'Donnerstag','Friday': 'Freitag'}

def create_weekly_rating_plot(db_session, dates, lang):
    """
    Creates a scatter plot displaying the weekly average ratings for a set of menu items over the specified date range.

    Args:
        db_session (Session): The database session used to retrieve the ratings data.
        dates (list): A list of strings containing the start and end date for the ratings period (in 'YYYY-MM-DD' format).
        lang (str): The language for displaying labels and titles. 'en' for English, 'de' for German.

    Returns:
        str: The HTML representation of the Plotly scatter plot, which can be embedded in a webpage.
    """
    ratings = get_ratings_of_the_week(db_session, dates)

    # If no ratings are found, return None
    if ratings.empty:
        return None
    
    ratings['day_of_week'] = pd.to_datetime(ratings['menuDate']).dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    ratings['day_of_week'] = pd.Categorical(
        ratings['day_of_week'],
        categories=day_order,
        ordered=True
    )
    ratings.sort_values(["day_of_week"], inplace=True)

    if lang == 'de':
        ratings['day_of_week'] = ratings['day_of_week'].map(day_translation_dict)
        
    # Create a scatter plot using go
    fig = go.Figure()

    ratings['hover_text'] = (
        "Menü: " + ratings['menu'] if lang == 'de' else "Menu: " + ratings['menuEng'] + "<br>" +
        "Mensa: " + ratings['location'] 
    )

    # Add scatter trace with Viridis color scale
    fig.add_trace(go.Scatter(
        x=ratings['day_of_week'],        
        y=ratings['avg_rating'],          
        mode='markers',                 
        marker=dict(
            size=10, 
            color=ratings['avg_rating'],  # Use avg_rating for color scale
            colorscale='Viridis',         # Apply the Viridis color scale
            colorbar=dict(
                titleside='right'
            )
        ),  
        text=ratings['hover_text'],             
        hovertemplate='<b>Day of Week:</b> %{x}<br>' +
                      '<b>Average Rating:</b> %{y}<br>' +
                      '%{text}<extra></extra>'  
    ))

    # Format the dates to "DD.MM.YYYY"
    formatted_start_date = datetime.strptime(dates[0], "%Y-%m-%d").strftime("%d.%m.%Y")
    formatted_end_date = datetime.strptime(dates[-1], "%Y-%m-%d").strftime("%d.%m.%Y")

    title = f'Weekly Average Ratings for <br>{formatted_start_date} to {formatted_end_date}' if lang == 'en' else f'Wöchentliche Durchschnittsbewertungen für <br>{formatted_start_date} bis {formatted_end_date}'
    
    # Set plot title and axis labels
    fig.update_layout(
        height=300,
        title=title,
        xaxis_title='Day of Week' if lang == 'en' else 'Wochentag', 
        yaxis_title='Average Rating' if lang == 'en' else 'Durchschnittliche Bewertung',
        template='plotly',
        xaxis=dict(
            tickangle=-45
        )
    )

    # Show the figure
    plot_html = pio.to_html(fig, full_html=False)
    return plot_html

        

def create_weekly_top_mensa_chart(db_session,lang,week_dates):
    """
    Creates a bar chart displaying the top three mensas based on average ratings for the specified week.

    Args:
        db_session (Session): The database session used to retrieve the ratings data.
        lang (str): The language for displaying labels and titles. 'en' for English, 'de' for German.
        week_dates (list): A list of two strings representing the start and end date of the week (in 'YYYY-MM-DD' format).

    Returns:
        str: The HTML representation of the Plotly bar chart, which can be embedded in a webpage.
    """

    top_three_mensas = get_top_three_mensas(db_session,week_dates)

    # Extract data for the chart
    locations = format_labels([item['location'] for item in top_three_mensas])
    avg_ratings = [item['avg_rating'] for item in top_three_mensas]

    # Create the bar trace
    mensa_trace = go.Bar(
        x=locations,
        y=avg_ratings,
        marker=dict(color=colors),
        text=[f"{rating:.1f}" for rating in avg_ratings],  
        textposition='auto'  
    )
    # Format the dates to "DD.MM.YYYY"
    formatted_start_date = datetime.strptime(week_dates[0], "%Y-%m-%d").strftime("%d.%m.%Y")
    formatted_end_date = datetime.strptime(week_dates[-1], "%Y-%m-%d").strftime("%d.%m.%Y")

    title = f'Top 3 Mensas of <br>{formatted_start_date} to {formatted_end_date}' if lang == 'en' else f'Top 3 Mensen für <br>{formatted_start_date} bis {formatted_end_date}'

    # Define the layout
    mensa_layout = go.Layout(
        title=dict(text=title),
        xaxis=dict(title='Mensa',tickangle=-45),
        yaxis=dict(title='Average Rating' if lang == 'en' else 'Durchschnittliche Bewertung'),
        template='plotly')

    # Create the figure
    fig = go.Figure(data=[mensa_trace], layout=mensa_layout)

    # Convert the figure to HTML
    plot_html = pio.to_html(fig, full_html=False)

    return plot_html

def create_weekly_top_dishes_chart(db_session,lang,week_dates):
    """
    Creates a bar chart displaying the top three dishes based on average ratings for the specified week.

    Args:
        db_session (Session): The database session used to retrieve the ratings data.
        lang (str): The language for displaying labels and titles. 'en' for English, 'de' for German.
        week_dates (list): A list of two strings representing the start and end date of the week (in 'YYYY-MM-DD' format).

    Returns:
        str: The HTML representation of the Plotly bar chart, which can be embedded in a webpage.
    """
 
    top_three_dishes = get_top_three_dishes(db_session,lang,week_dates)
    # Extract data for the chart
    dish_names = format_labels([item['dish_name'] for item in top_three_dishes])
    avg_ratings = [item['avg_rating'] for item in top_three_dishes]

    # Create the bar trace
    dish_trace = go.Bar(
        x=dish_names,
        y=avg_ratings,
        marker=dict(color=colors),
        text=[f"{rating:.1f}" for rating in avg_ratings],  
        textposition='auto'  
    )
    # Format the dates to "DD.MM.YYYY"
    formatted_start_date = datetime.strptime(week_dates[0], "%Y-%m-%d").strftime("%d.%m.%Y")
    formatted_end_date = datetime.strptime(week_dates[-1], "%Y-%m-%d").strftime("%d.%m.%Y")

    title = f'Top 3 Dishes of <br>{formatted_start_date} to {formatted_end_date}' if lang == 'en' else f'Top 3 Gerichte von <br>{formatted_start_date} bis {formatted_end_date}'

    # Define the layout
    dish_layout = go.Layout(
        title=dict(text=title),
        xaxis=dict(
            title='Dish' if lang == 'en' else 'Menü',
            tickangle=-45,
            automargin=True,
            tickmode='array',
            tickvals=list(range(len(dish_names))),
            ticktext=dish_names
        ),
        yaxis=dict(
            title='Average Rating' if lang == 'en' else 'Durchschnittliche Bewertung'
        ),
        template='plotly'
    )

    # Create the figure
    fig = go.Figure(data=[dish_trace], layout=dish_layout)

    # Convert the figure to HTML
    plot_html = pio.to_html(fig, full_html=False)

    return plot_html


def plot_rating_histogram(db_session, dates, dish):
    """
    Creates a histogram of ratings for a specific dish (or the first dish in the data) over a given week.

    Args:
        db_session (Session): The database session used to retrieve dish rating data.
        dates (list): A list containing two strings representing the start and end date of the week (in 'YYYY-MM-DD' format).
        dish (str or None): The name of the dish to plot the ratings for. If None, the first available dish will be used.

    Returns:
        tuple: A tuple containing:
            - plot_html (str): The HTML representation of the Plotly histogram for embedding.
            - unique_menus (list): A list of unique menu names available for selection.
    """
    # Get the data and filter it by the specified dish
    dishes_df = get_dishes_and_rating_by_week(db_session, dates)
    unique_menus = dishes_df['menu'].unique().tolist()

    if dish is not None:
        df = dishes_df[dishes_df['menu'] == dish]
    else:
        df = dishes_df[dishes_df['menu'] == unique_menus[0]]

    count = df['rating'].value_counts().reindex(range(1, 6), fill_value=0)

    # Create the Plotly graph
    fig = go.Figure(data=[
        go.Bar(
            x=count.index,  
            y=count.values, 
            text=count.values, 
            textposition='auto'
        )
    ])

    # Customize layout
    fig.update_layout(
        title="Unique Count of Ratings",
        xaxis_title="Ratings",
        yaxis_title="Count",
        xaxis=dict(tickmode='array', tickvals=[1, 2, 3, 4, 5]),
        template="plotly_white"
    )

    # Convert the plot to an HTML string
    plot_html = pio.to_html(fig, full_html=False)

    return plot_html,unique_menus


def plot_pie_chart(db_session, week_dates, lang):
    """
    Creates a pie chart to visualize the distribution of taste clusters for a specified week.

    Args:
        db_session (Session): The database session used to retrieve the cluster similarity data.
        week_dates (list): A list containing two strings representing the start and end date of the week (in 'YYYY-MM-DD' format).
        lang (str): The language for the labels and titles.

    Returns:
        str: The HTML string representation of the Plotly pie chart, which can be embedded in a webpage.
    """

    cluster_counts_df = get_cluster_similarity_for_week(db_session, week_dates,lang)

    # Extract cluster names and their counts
    labels = cluster_counts_df['cluster_name']
    values = cluster_counts_df['count']

    # Create the pie chart
    fig = go.Figure(
        data=[go.Pie(
            labels=labels, 
            values=values, 
            hoverinfo='label+percent+value',
            marker=dict(colors=sequential.Viridis)  
        )]
    )
    # Format the dates to "DD.MM.YYYY"
    formatted_start_date = datetime.strptime(week_dates[0], "%Y-%m-%d").strftime("%d.%m.%Y")
    formatted_end_date = datetime.strptime(week_dates[-1], "%Y-%m-%d").strftime("%d.%m.%Y")

    title = f'Taste Cluster Distribution for <br>{formatted_start_date} to {formatted_end_date}' if lang == 'en' else f'Geschmackscluster Verteilung für <br>{formatted_start_date} bis {formatted_end_date}'

    # Update layout for styling
    fig.update_layout(
        title_text=title,
        annotations=[dict(
            text="", 
            x=0.5, y=0.5, 
            font_size=20, 
            showarrow=False
        )],
        showlegend=True
    )

    # Display the figure
    plot_html = pio.to_html(fig, full_html=False)

    return plot_html


def top_mensa_for_user_chart(db_session, user_name, lang):
    """
    Generates a bar chart showing the top mensas for a specific user and their average ratings.

    Args:
        db_session (Session): The database session used to query data.
        user_name (str): The name of the user whose favorite mensas will be displayed.
        lang (str): The language for the chart labels ('en' for English, 'de' for German).

    Returns:
        str: The HTML string of the Plotly chart, ready to be embedded in a webpage.
    """
    
    favorite_mensas = get_favorite_mensas_of_user(db_session, user_name, lang)        

    fig = go.Figure()

    # Add bar chart data to the figure
    fig.add_trace(go.Bar(
        x=format_labels_mensas([mensa[0] for mensa in favorite_mensas]),
        y=[mensa[1] for mensa in favorite_mensas],
        marker_color=['#4F46E5', '#6366F1', '#818CF8'],
        name='Mensa Ratings'
    ))

    # Update layout settings
    fig.update_layout(
        autosize=True,
        xaxis={
            'title': {'text': 'Mensa', 'standoff': 20},
            'tickangle': -45,
            'automargin': True
        },
        yaxis={
            'title': 'Durchschnittliche Bewertung' if lang == 'de' else 'Average Rating'
        },
        title='Top Mensas Chart'
    )

    # Convert the figure to HTML with responsive configuration
    plot_html = pio.to_html(fig, full_html=False, config={'responsive': True})
    return plot_html