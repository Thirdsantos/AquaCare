from flask import Flask, Blueprint
from flasgger import Swagger

def create_app():
  app = Flask(__name__)
  
  app.config['SWAGGER'] = {
        'title': 'My API Docs',
        'uiversion': 3,
    }

  from app.routes.sensors import sensors_bp
  app.register_blueprint(sensors_bp)
  from app.routes.ai_route import ai_bp
  app.register_blueprint(ai_bp)
  from app.routes.main import main_bp
  app.register_blueprint(main_bp)

  Swagger(app, parse=True)

  

  return app

