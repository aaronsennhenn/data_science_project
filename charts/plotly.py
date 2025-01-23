from flask import request
import plotly.graph_objects as go
import plotly.io as pio
from plotly.colors import sequential
from db.db_read import get_combined_dishes

# Define the colors
colors = ['#4F46E5', '#6366F1', '#818CF8']

def format_labels(labels):
    def insert_br_every_n_words(label, n=2):
        words = label.split()
        return '<br>'.join([' '.join(words[i:i+n]) for i in range(0, len(words), n)])
    return [insert_br_every_n_words(label) for label in labels]

def generate_price_chart(db_session, selected_category, selected_price_type, show_icons):
    ### Get Data ###
    df = get_combined_dishes(db_session)

    # Default initial values
    if selected_category == "initial":
        selected_category = df['menuLine'].unique()[0]

    # Filter the DataFrame
    filtered_df = df[df['menuLine'] == selected_category]

    # Define the colors
    PLOT_COLORS = sequential.ice

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
            orientation='h',  
            yanchor='top',   
            y=-0.2,           
            xanchor='center',
            x=0.5   
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
        height = 500,
        width = 500
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

    formatted_categories = format_labels(categories)

    fig = go.Figure()

    # Add user ratings to the bar chart
    fig.add_trace(go.Bar(
        x=formatted_categories,
        y=user_values,
        name="Your Ratings",
        marker=dict(color=colors[1])
    ))

    # Add all users' ratings to the bar chart with transparency
    fig.add_trace(go.Bar(
        x=formatted_categories,
        y=all_values,
        name="Other Users' Ratings",
        marker=dict(color=colors[2]),
        opacity=0.5
    ))

    # Update layout for better visualization
    fig.update_layout(
        xaxis={
        'title': {
            'text': 'Categories',
            'standoff': 20  
        },
        'tickangle': -45,
        'automargin': True  
        },
        yaxis={
            'title': 'Average Rating'
        },
        barmode="group",
        xaxis_tickangle=-45,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        height = 400,
        width = 550
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
