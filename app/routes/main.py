from flask import Blueprint, request, render_template

main_bp = Blueprint("main",__name__)

@main_bp.route('/')
def index():
  return render_template("index.html")
