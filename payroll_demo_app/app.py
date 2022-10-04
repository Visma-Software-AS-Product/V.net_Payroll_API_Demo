from flask import Flask, url_for, redirect, session

# Creates the Flask-application 
app = Flask(__name__) 
# Sets a secret key for the session cookie
app.secret_key = 'SECRET KEY'
