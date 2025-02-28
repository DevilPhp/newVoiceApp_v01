import os
from flask import Flask

def createApp(configClass=None):
    #Creating default application
    app = Flask(__name__)

    if configClass is None:
        from app.config import Config
        app.config.from_object(Config)
    else:
        app.config.from_object(configClass)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app.extensions import db, migrate
    db.init_app(app)
    migrate.init_app(app, db)

    from app.models import chat, message

    with app.app_context():
        db.create_all()

    from app.blueprints import bp as mainBp
    app.register_blueprint(mainBp)

    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
        }

    return app
