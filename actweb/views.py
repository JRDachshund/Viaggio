from flask import Blueprint, render_template, request, session, Response, jsonify

views = Blueprint("views", __name__)

@views.route("/", methods=["GET", "POST"])
def home():
    return "Hello World"
