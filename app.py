from flask import Flask, request, session, redirect, url_for, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dining_facilities')
def dining_facilities():
   return render_template('dining_facilities')

if __name__ == "__main__":
    # hier wird nix verändert
    app.run()