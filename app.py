from flask import Flask, request, session, redirect, url_for, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dining_facilities')
def dining_facilities():
   return render_template('dining_facilities.html')

@app.route('/cafeteria_mensa_pkl')
def cafeteria_mensa_pkl():
   return render_template('cafeteria_mensa_pkl.html')

@app.route('/cafeteria_mst')
def cafeteria_mst():
   return render_template('cafeteria_mst.html')

@app.route('/mensa_mst')
def mensa_mst():
   return render_template('mensa_mst.html')

@app.route('/cafeteria_wil')
def cafeteria_wil():
   return render_template('cafeteria_wil.html')

@app.route('/mensa_wil')
def mensa_wil():
   return render_template('mensa_wil.html')

if __name__ == "__main__":
    # hier wird nix verändert
    app.run()