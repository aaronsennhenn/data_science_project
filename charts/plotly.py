from flask import request
import plotly.graph_objects as go
import plotly.io as pio
from plotly.colors import sequential
from db.db_read import get_combined_dishes,get_ratings_of_the_week,get_top_three_mensas,get_top_three_dishes,get_dishes_and_rating_by_week
import pandas as pd
from datetime import datetime
import json


# Define the colors
colors = ['#4F46E5', '#6366F1', '#818CF8']

# Function to format x-axis labels with line breaks
def format_labels(labels):
    return [label.replace(', ', '<br>') for label in labels]

def generate_price_chart(db_session, selected_category, selected_price_type, show_icons):
    # Get data
    df = get_combined_dishes(db_session)

    # Default initial values
    if selected_category == "initial":
        selected_category = df['menuLine'].unique()[0]

    # Filter the DataFrame
    filtered_df = df[df['menuLine'] == selected_category]

    # Define the colors
    PLOT_COLORS = sequential.Jet

    # Create the Plotly figure
    fig = go.Figure()

    # Add traces based on the toggle state
    if show_icons:
        unique_icons = filtered_df['icons_clean'].unique()
        for i, icon in enumerate(unique_icons):
            icon_data = filtered_df[filtered_df['icons_clean'] == icon]
            fig.add_scatter(
                x=icon_data['menuDate'],
                y=icon_data[selected_price_type],
                mode='markers',
                name=f'{icon}',
                marker=dict(color=PLOT_COLORS[i % len(PLOT_COLORS)])
            )
    else:
        fig.add_scatter(
            x=filtered_df['menuDate'],
            y=filtered_df[selected_price_type],
            mode='markers',
            name='All Prices'
        )

    # Update layout
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title=selected_price_type.capitalize(),
        legend=dict(
            x=-0.2,  # Position legend to the left of the plot
            y=0.5,   # Center the legend vertically
            xanchor="left",  # Anchor the legend box to the left
            yanchor="middle",  # Anchor the legend box to the middle
        )
    )

    # Convert the Plotly figure to HTML
    #plot_html = pio.to_html(fig, full_html=False,config={'responsive': True})
    plot_html = pio.to_html(fig, full_html=False)

    return plot_html,df['menuLine'].unique()

def create_taste_radarchart(df, taste_label, similarity):

    r = df[similarity].tolist()  
    theta = df[taste_label].tolist()  

    #Create Radar Chart
    fig = go.Figure()

    #Add player's data to the chart
    fig.add_trace(go.Scatterpolar(
        r=r, 
        theta=theta, 
        fill='toself',  
        marker=dict(color=colors[0]),
        name = None,
        hoverinfo = 'none'
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
        height = 560,
        width = 560
    )

    # Convert figure to html format
    fig_html = pio.to_html(fig, full_html=False)
    
    return fig_html

def plot_average_ratings(user_ratings, all_ratings):
    """
    Plots the average ratings of a specific user alongside the average ratings of all users using Plotly.

    Parameters:
        user_ratings (dict): Average ratings for a specific user.
        all_ratings (dict): Average ratings for all users.
    """
    categories = sorted(set(user_ratings.keys()).union(all_ratings.keys()))
    user_values = [user_ratings.get(category, 0) for category in categories]
    all_values = [all_ratings.get(category, 0) for category in categories]

    fig = go.Figure()

    # Add user ratings to the bar chart
    fig.add_trace(go.Bar(
        x=categories,
        y=user_values,
        name="Your Ratings",
        marker=dict(color=colors[1])
    ))

    # Add all users' ratings to the bar chart with transparency
    fig.add_trace(go.Bar(
        x=categories,
        y=all_values,
        name="Other Users' Ratings",
        marker=dict(color=colors[2]),
        opacity=0.5
    ))

    # Update layout for better visualization
    fig.update_layout(
        xaxis_title="Categories",
        yaxis_title="Average Rating",
        barmode="group",
        xaxis_tickangle=-45
    )

    fig_html = pio.to_html(fig, full_html=False)
    return fig_html


def create_past_6_month_spending_chart(df, user_type):
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
        plot_bgcolor='white',  
        paper_bgcolor='white',
        yaxis=dict(
            showgrid=True,  # Enable grid lines on the x-axis
            gridcolor='lightgray',  # Set grid line color
    ))
    
    # Convert the figure to HTML and return it
    fig_html = pio.to_html(fig, full_html=False)

    return fig_html


def create_weekly_rating_plot(db_session,dates):

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
        
    # Create a scatter plot using go
    fig = go.Figure()

    ratings['hover_text'] = (
    "Menu: " + ratings['menu'] + "<br>" +
    "Location: " + ratings['location']
)
    # Add scatter trace
    fig.add_trace(go.Scatter(
        x=ratings['day_of_week'],        
        y=ratings['avg_rating'],          
        mode='markers',                 
        marker=dict(size=10, color='blue'),  
        text=ratings['hover_text'],             
        hovertemplate='<b>Day of Week:</b> %{x}<br>' +
                    '<b>Average Rating:</b> %{y}<br>' +
                    '%{text}<extra></extra>'  
    ))

    # Format the dates to "DD.MM.YYYY"
    formatted_start_date = datetime.strptime(dates[0], "%Y-%m-%d").strftime("%d.%m.%Y")
    formatted_end_date = datetime.strptime(dates[-1], "%Y-%m-%d").strftime("%d.%m.%Y")


    # Set plot title and axis labels
    fig.update_layout(
        title=f'Weekly Average Ratings for {formatted_start_date} to {formatted_end_date}',
        xaxis_title='Day of Week',
        yaxis_title='Average Rating',
        template='plotly'
    )


    # Show the figure
    plot_html = pio.to_html(fig, full_html=False)
    return plot_html
        

def create_weekly_top_mensa_chart(db_session,lang):
            
    top_three_mensas = get_top_three_mensas(db_session)

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

    # Define the layout
    mensa_layout = go.Layout(
        xaxis=dict(
            title='Mensa',
            tickangle=0
        ),
        yaxis=dict(
            title='Average Rating' if lang == 'en' else 'Durchschnittliche Bewertung'
        ),
        template='plotly' 
    )

    # Create the figure
    fig = go.Figure(data=[mensa_trace], layout=mensa_layout)

    # Convert the figure to HTML
    plot_html = pio.to_html(fig, full_html=False)

    return plot_html

def create_weekly_top_dishes_chart(db_session,lang):

    top_three_dishes = get_top_three_dishes(db_session,lang)
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

    # Define the layout
    dish_layout = go.Layout(
        xaxis=dict(
            title='Dish' if lang == 'en' else 'Menü',
            tickangle=0
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