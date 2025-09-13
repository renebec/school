from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_control = db.Column(db.String(50), unique=True)
    apellido_paterno = db.Column(db.String(100))
    apellido_materno = db.Column(db.String(100))
    nombres = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    carrera = db.Column(db.String(100))
    semestre = db.Column(db.String(10))
    grupo = db.Column(db.String(10))
    rol = db.Column(db.String(20), default='alumno')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone("America/Mexico_City")))

class Class(db.Model):
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    docente_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone("America/Mexico_City")))

class Mat1(db.Model):
    __tablename__ = 'mat1'
    
    id = db.Column(db.Integer, primary_key=True)
    plan = db.Column(db.Integer)
    asig = db.Column(db.String(200))
    meta = db.Column(db.Text)
    prop = db.Column(db.Text)
    temas = db.Column(db.Text)
    plantel = db.Column(db.String(100))
    ciclo = db.Column(db.String(50))
    periodo = db.Column(db.String(50))
    carrera = db.Column(db.String(100))
    semestre = db.Column(db.String(10))
    grupos = db.Column(db.String(50))
    horas_sem = db.Column(db.String(10))
    docenteID = db.Column(db.String(50))
    imparte = db.Column(db.String(100))
    parcial = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone("America/Mexico_City")))
    pdf_url = db.Column(db.String(500))

class ActividadInoc(db.Model):
    __tablename__ = 'actividades_inoc'
    
    id = db.Column(db.Integer, primary_key=True)
    actividad_num = db.Column(db.String(20))
    apellido_paterno = db.Column(db.String(100))
    apellido_materno = db.Column(db.String(100))
    nombres = db.Column(db.String(100))
    carrera = db.Column(db.String(100))
    semestre = db.Column(db.String(10))
    grupo = db.Column(db.String(10))
    pdf_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone("America/Mexico_City")))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    calificacion = db.Column(db.Float)

class StudentsClasses(db.Model):
    __tablename__ = 'students_classes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    grupo = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone("America/Mexico_City")))