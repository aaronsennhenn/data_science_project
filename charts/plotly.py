from flask import request
import plotly.graph_objects as go
import plotly.io as pio
from db.db_read import get_combined_dishes

def generate_price_chart(db_session, selected_category, selected_price_type, show_icons):
    ### Get Data ###
    df = get_combined_dishes(db_session)

    # Default initial values
    if selected_category == "initial":
        selected_category = df['menuLine'].unique()[0]

    # Filter the DataFrame
    filtered_df = df[df['menuLine'] == selected_category]

    # Create the Plotly figure
    fig = go.Figure()

    # Add traces based on the toggle state
    if show_icons:
        unique_icons = filtered_df['icons_clean'].unique()
        for icon in unique_icons:
            icon_data = filtered_df[filtered_df['icons_clean'] == icon]
            fig.add_scatter(
                x=icon_data['menuDate'],
                y=icon_data[selected_price_type],
                mode='markers',
                name=f'{icon}'
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
        title=f'{selected_price_type.capitalize()} Over Time for Category {selected_category}',
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

    # Create Radar Chart
    fig = go.Figure()

    # Add player's data to the chart
    fig.add_trace(go.Scatterpolar(
        r=r,  # Player stats values
        theta=theta,  # Player stats labels
        fill='toself',  # Fill the area under the line
        marker=dict(color='blue'),
        name = 'This is your Taste Profile'
    ))

    # Update layout for better appearance
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=False,
                range=[0, 1]
            )
        ),
        showlegend=True
    )

    # Convert figure to html format
    fig_html = pio.to_html(fig, full_html=False)
    
    return fig_html