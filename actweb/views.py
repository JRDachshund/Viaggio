from flask import Blueprint, render_template, request, session, Response, jsonify

views = Blueprint("views", __name__)

@views.route("/", methods=["GET", "POST"])
def home():
    return render_template('homePage.html')

@views.route("/map", methods=["GET", "POST"])
def map():
    return render_template('map.html')

@views.route("/destinationSelection", methods=["GET", "POST"])
def destinationSelection():
    return render_template('destinationSelection.html')

@views.route("/transportSelection", methods=["GET", "POST"])
def transportSelection():
    return render_template('transportSelection.html')

@views.route("/accommodationSelection", methods=["GET", "POST"])
def accommodationSelection():
    return render_template('accommodationSelection.html')

@views.route("/tripSummary", methods=["GET", "POST"])
# Hier sieht man die Übersicht über die geplante Reise und kann Unterkünfte buchen
def tripSummary(): 
    return render_template('tripSummary.html')

