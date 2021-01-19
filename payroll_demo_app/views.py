from flask import Flask, render_template
from . import app
from . import payrollapi

# Default route for the application to serve the page home.html
@app.route("/")
def home():
    return render_template("home.html")
