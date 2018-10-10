from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    text = db.Column(db.String(128))
    sound = db.Column(db.String(128))
    image = db.Column(db.String(128))
