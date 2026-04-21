from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Relato(db.Model):
    id = db.Column(db.Integer

class Relato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.String(20))
    
    def __repr__(self):
        return f'<Relato {self.titulo}>'

