import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pytz
import mysql.connector
import pymysql

db_connection_string = os.environ['DB_CONNECTION_STRING']
engine = create_engine(db_connection_string,
      connect_args={
            "ssl": { 
              "ca": "/etc/ssl/certs/ca-certificates.crt"
                   }
                  }
            )

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SessionLocal = sessionmaker(bind=engine)

def get_db_session():
    return SessionLocal()

def load_pg_from_db():
    try:
      with engine.connect() as conn:
          result = conn.execute(text("SELECT * FROM inocAgro"))
          pg = result.mappings().all()
          return pg
    except Exception as e:
      print(f"DB ERROR: {e}")
      return None

      #result_all = result.all()
      #tipo = type(result_all)
      #tipo_2 = type(result_all[0])
      #print(tipo)
      #print(tipo_2)
      #print(result_all)
    #otro comentario

def load_pgn_from_db(id):
  try:
    with engine.connect() as conn:
      result = conn.execute(
        text("SELECT * FROM inocAgro WHERE id = :val"),
        {"val":id}
      )
      row = result.mappings().first()  # <- dict, no tupla
      return dict(row) if row else None
  except Exception as e:
    print(f"DB ERROR: {e}")
    return None



# Insert a new actividad record
def insert_actividad(session, actividad_num, apellido_paterno, apellido_materno, nombres, carrera, semestre, grupo, numero_control, pdf_url, created_at):
    created_at = datetime.now(pytz.timezone("America/Mexico_City"))
    try:
            query = text("""
                INSERT INTO actividades_inoc (
                    actividad_num,
                    apellido_paterno,
                    apellido_materno,
                    nombres,
                    carrera,
                    semestre,
                    grupo,
                    numero_control,
                    pdf_url,
                    created_at
                )
                VALUES (
                    :actividad_num,
                    :apellido_paterno,
                    :apellido_materno,
                    :nombres,
                    :carrera,
                    :semestre,
                    :grupo,
                    :numero_control,
                    :pdf_url,
                    :created_at
                )
            """)
            session.execute(query, {
                "actividad_num": actividad_num,
                "apellido_paterno": apellido_paterno,
                "apellido_materno": apellido_materno,
                "nombres": nombres,
                "carrera": carrera,
                "semestre": semestre,
                "grupo": grupo,
                "numero_control": numero_control,
                "pdf_url": pdf_url,
                "created_at": created_at
            })
            session.commit()  # Make sure to commit the transaction
    except Exception as e:
        print(f"DB ERROR while inserting actividad: {e}")
        session.rollback()  # Rollback in case of error
        return False
    return True


# Get user data by username (login verification)
def get_user_from_database(username):
    try:
        session = get_db_session()
        result = session.execute(
            text("SELECT * FROM users WHERE username = :val"),
            {"val": username}
        )
        row = result.mappings().first()
        session.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"DB ERROR: {e}")
        return None



# Register a new user in the database
def register_user(session, numero_control, apellido_paterno, apellido_materno, nombres, username, password, carrera, semestre, grupo):
    password = password  # You might want to hash this password
    mexico_time = datetime.now(pytz.timezone("America/Mexico_City"))
    try:
        sql = text("""
            INSERT INTO users (numero_control, apellido_paterno, apellido_materno, nombres, username, password, carrera, semestre, grupo, created_at)
            VALUES (:numero_control, :apellido_paterno, :apellido_materno, :username,  :nombres, :password, :carrera, :semestre, :grupo, :created_at)
        """)
        session.execute(sql, {
            "numero_control": numero_control,
            "apellido_paterno": apellido_paterno,
            "apellido_materno": apellido_materno,
            "nombres": nombres,
            "username": username,
            "password": password,
            "carrera": carrera,
            "semestre": semestre,
            "grupo": grupo
        })
        session.commit()  # Commit the transaction
    except Exception as e:
        print(f"DB ERROR during user registration: {e}")
        session.rollback()  # Rollback in case of error
        return False
    return True
      