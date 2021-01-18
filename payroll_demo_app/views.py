from flask import Flask, render_template
from . import app
from . import payrollapi

@app.route("/")
def home():
    return render_template("home.html")
