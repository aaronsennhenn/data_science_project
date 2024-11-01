from flask import Flask, render_template,request, jsonify
from scraper import run_scraper, get_dates

app = Flask(__name__)

@app.route('/')
def index():
    # You can pass dynamic options to the dropdown if needed
    mensa_options = ["Wilhelmstraße", "Morgenstelle", "Prinz Karl"]
    date_options = get_dates(4)

    return render_template('index.html', options=mensa_options, dates=date_options)

@app.route('/submit', methods=['POST'])
def display_res():

    # get option result
    selected_mensa = request.form.get('dropdown')
    selected_date = request.form.get("date")

    # Ensure both dropdowns are selected
    if not selected_mensa or not selected_date:
        return "Please select both a mensa and a date!", 400

    # get scraper results (dataframe)
    scraper_res = run_scraper(selected_mensa,selected_date)

    # daily dish
    table_dish = scraper_res[scraper_res["menuLine"] == "Angebot des Tages"][["menuLine","menu","studentPrice"]]
    table_dish_vegan = scraper_res[scraper_res["menuLine"] == "Angebot d. Tages vegan"][["menuLine","menu","studentPrice"]]
    table_dish_veget = scraper_res[scraper_res["menuLine"] == "Angebot d. Tages veget."][["menuLine","menu","studentPrice"]]

    # Convert the dataframe to HTML
    #df_html = scraper_res.to_html(classes='dataframe', header="true", index=False)
    table_dish = table_dish.to_dict(orient="records")
    table_dish_vegan = table_dish_vegan.to_dict(orient="records")

    # Render the template and pass the dataframe HTML to it
    return render_template('result.html', table_dish=table_dish,table_dish_vegan=table_dish_vegan,table_dish_veget=table_dish_veget,selected_option=selected_mensa, selected_date=selected_date)

if __name__ == '__main__':
    app.run(debug=True)


