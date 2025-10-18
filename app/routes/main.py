from flask import Blueprint, request, render_template

main_bp = Blueprint("main",__name__)

@main_bp.route('/')
def index():
  """Serve the index page for basic health check and UI landing."""
  return render_template("index.html")

