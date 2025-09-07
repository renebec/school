import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pytz
import pymysql
from flask_bcrypt import generate_password_hash
#Estructura básica Flask para registro

from flask import Flask, request, render_template, redirect, url_for, flash

from datetime import datetime
import pytz

db_connection_string = os.environ['DB_CONNECTION_STRING']
engine = create_engine(db_connection_string,
      connect_args={
            "ssl": { 
              "ca": "/etc/ssl/certs/ca-certificates.crt"
                   }
                  }
            )

#Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SessionLocal = sessionmaker(bind=engine)

def get_db_session():
    return SessionLocal()


def load_pg_from_db():
    try:
      with engine.connect() as conn:
          result = conn.execute(text("SELECT * FROM mat1"))
          pg = result.mappings().all()
          return pg
    except Exception as e:
      print(f"DB ERROR: {e}")
      return None

def load_pg_from_db2():
    try:
      with engine.connect() as conn:
          #result = conn.execute(text("SELECT * FROM planInocAgro ORDER BY created_at DESC"))
          result = conn.execute(text("SELECT * FROM mat1"))
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


def load_plan_from_db(id):
    try:
      with engine.connect() as conn:
          result = conn.execute(text("SELECT * FROM mat1 WHERE id = :val"),
              {"val":id}
            )
          row = result.mappings().first()
          return dict(row) if row else None
    except Exception as e:
      print(f"DB ERROR: {e}")
      return None





def load_pgn_from_db(id):
  try:
    with engine.connect() as conn:
      result = conn.execute(
        text("SELECT * FROM mat1 WHERE id = :val"),
        {"val":id}
      )
      row = result.mappings().first()  # <- dict, no tupla
      return dict(row) if row else None
  except Exception as e:
    print(f"DB ERROR: {e}")
    return None



# Insert a new actividad record
def insert_actividad_simple(session, actividad_num, apellido_paterno, apellido_materno, nombres, carrera, semestre, grupo, pdf_url, created_at):
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
                "pdf_url": pdf_url,
                "created_at": created_at
            })
            session.commit()  # Make sure to commit the transaction
            session.close()
    except Exception as e:
        print(f"DB ERROR Error al cargar la actividad, intente más tarde: {e}")
        session.rollback()  # Rollback in case of error
        return False
    return True




def insert_plan(
    session, plan, asig, meta, prop, temas, plantel, ciclo, periodo,
    carrera, semestre, grupos, horas_sem, docenteID, imparte, parcial,
    trAsigP1, trtemaP1, trAsigP2, trtemaP2, trAsigP3, trtemaP3,
    trAsigP4, trtemaP4, trAsigM1, trtemaM1, trAsigM2, trtemaM2,
    trAsigM3, trtemaM3, trAsigM4, trtemaM4,
    apDur, apEv, apIns, apPond, apAct,
    deDur, deEv, deIns, dePond, deAct,
    ciDur, ciEv, ciIns, ciPond, ciAct,
    materiales, equipo, fuentes,
    elabora, revisa, avala, cve,
    created_at=None, pdf_url=None, parPond=None
):
    # Si no se proporciona created_at, se asigna la hora actual de México
    if created_at is None:
        created_at = datetime.now(pytz.timezone("America/Mexico_City"))
        
    
    # Preparación de parámetros para INSERT y UPDATE
    params = {
        "plan": plan, "asig": asig, "meta": meta, "prop": prop, "temas": temas,
        "plantel": plantel, "ciclo": ciclo, "periodo": periodo, "carrera": carrera,
        "semestre": semestre, "grupos": grupos, "horas_sem": horas_sem,
        "docenteID": docenteID, "imparte": imparte, "parcial": parcial,
        "trAsigP1": trAsigP1, "trtemaP1": trtemaP1, "trAsigP2": trAsigP2,
        "trtemaP2": trtemaP2, "trAsigP3": trAsigP3, "trtemaP3": trtemaP3,
        "trAsigP4": trAsigP4, "trtemaP4": trtemaP4,
        "trAsigM1": trAsigM1, "trtemaM1": trtemaM1, "trAsigM2": trAsigM2,
        "trtemaM2": trtemaM2, "trAsigM3": trAsigM3,
        "trtemaM3": trtemaM3, "trAsigM4": trAsigM4, "trtemaM4": trtemaM4,
        "apDur": apDur, "apEv": apEv, "apIns": apIns, "apPond": apPond,
        "apAct": apAct,
        "deDur": deDur, "deEv": deEv, "deIns": deIns, "dePond": dePond,
        "deAct": deAct,
        "ciDur": ciDur, "ciEv": ciEv, "ciIns": ciIns, "ciPond": ciPond,
        "ciAct": ciAct,
        "materiales": materiales, "equipo": equipo, "fuentes": fuentes,
        "elabora": elabora, "revisa": revisa, "avala": avala, "cve": cve,
        "created_at": created_at, "pdf_url": pdf_url, "parPond": parPond
    }

    try:
        # Definición de la sentencia INSERT
        insert_query = text("""
            INSERT INTO mat1 (
                plan, asig, prop, temas, plantel, ciclo, meta, periodo, carrera,
                semestre, grupos, horas_sem, docenteID, imparte, parcial,
                trAsigP1, trtemaP1, trAsigP2, trtemaP2, trAsigP3, trtemaP3,
                trAsigP4, trtemaP4, trAsigM1, trtemaM1, trAsigM2, trtemaM2,
                trAsigM3, trtemaM3, trAsigM4, trtemaM4,
                apDur, apEv, apIns, apPond, apAct, deDur, deEv, deIns, dePond,
                deAct, ciDur, ciEv, ciIns, ciPond, ciAct,
                materiales, equipo, fuentes,
                elabora, revisa, avala, cve, created_at, pdf_url, parPond
            ) VALUES (
                :plan, :asig, :prop, :temas, :plantel, :ciclo, :meta, :periodo, :carrera,
                :semestre, :grupos, :horas_sem, :docenteID, :imparte, :parcial,
                :trAsigP1, :trtemaP1, :trAsigP2, :trtemaP2, :trAsigP3, :trtemaP3,
                :trAsigP4, :trtemaP4, :trAsigM1, :trtemaM1, :trAsigM2, :trtemaM2,
                :trAsigM3, :trtemaM3, :trAsigM4, :trtemaM4, :apDur, :apEv, :apIns,
                :apPond, :apAct, :deDur, :deEv, :deIns, :dePond, :deAct,
                :ciDur, :ciEv, :ciIns, :ciPond, :ciAct, :materiales, :equipo,
                :fuentes, :elabora, :revisa, :avala, :cve, :created_at, :pdf_url, :parPond
            )
        """)
        result = session.execute(insert_query, params)
        session.commit()
        print("✅ Plan insertado correctamente")
        return result.lastrowid

    except pymysql.err.IntegrityError as e:
        if "1062" in str(e):  # Detección de clave duplicada
            print("⚠️ Plan duplicado detectado. Actualizando...")

            update_query = text("""
                UPDATE mat1 SET
                    plan = :plan, asig = :asig, meta = :meta, prop = :prop, temas = :temas,
                    plantel = :plantel, ciclo = :ciclo, periodo = :periodo, carrera = :carrera,
                    semestre = :semestre, grupos = :grupos, horas_sem = :horas_sem,
                    docenteID = :docenteID, imparte = :imparte, parcial = :parcial,
                    trAsigP1 = :trAsigP1, trtemaP1 = :trtemaP1, trAsigP2 = :trAsigP2,
                    trtemaP2 = :trtemaP2, trAsigP3 = :trAsigP3, trtemaP3 = :trtemaP3,
                    trAsigP4 = :trAsigP4, trtemaP4 = :trtemaP4,
                    trAsigM1 = :trAsigM1, trtemaM1 = :trtemaM1,
                    trAsigM2 = :trAsigM2, trtemaM2 = :trtemaM2,
                    trAsigM3 = :trAsigM3, trtemaM3 = :trtemaM3,
                    trAsigM4 = :trAsigM4, trtemaM4 = :trtemaM4,
                    apDur = :apDur, apEv = :apEv, apIns = :apIns, apPond = :apPond,
                    apAct = :apAct,
                    deDur = :deDur, deEv = :deEv, deIns = :deIns, dePond = :dePond,
                    deAct = :deAct,
                    ciDur = :ciDur, ciEv = :ciEv, ciIns = :ciIns, ciPond = :ciPond,
                    ciAct = :ciAct,
                    materiales = :materiales, equipo = :equipo, fuentes = :fuentes,
                    elabora = :elabora, revisa = :revisa, avala = :avala,
                    created_at = :created_at, pdf_url = :pdf_url, parPond = :parPond
                WHERE plan = :plan
            """)

            session.execute(update_query, params)
            session.commit()
            print("✅ Plan actualizado correctamente")
            return params.get("plan")  # Puedes retornar el identificador si corresponde

        # Si no es por duplicado, propaga el error
        raise

    except Exception as e:
        print(f"❌ DB ERROR al cargar la planeación: {e}")
        session.rollback()
        return False

    finally:
        session.close()






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



def insert_actividad_with_user_class(session, actividad_num, apellido_paterno, apellido_materno, nombres,
     carrera, semestre, grupo, pdf_url, created_at, user_id, class_id):
    try:
        query = text("""
        INSERT INTO actividades_inoc (
        actividad_num, apellido_paterno, apellido_materno, nombres,
        carrera, semestre, grupo, pdf_url, created_at, user_id, class_id
        )
        VALUES (
        :actividad_num, :apellido_paterno, :apellido_materno, :nombres,
        :carrera, :semestre, :grupo, :pdf_url, :created_at, :user_id, :class_id
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
        "pdf_url": pdf_url,
        "created_at": created_at,
        "user_id": user_id,
        "class_id": class_id
        })
        session.commit()
        return True
    except Exception as e:
        print(f"DB ERROR insert_actividad: {e}")
        session.rollback()
        return False
    finally:
        session.close()
#-----

def get_user_by_id(user_id):
    session = get_db_session()
    try:
        result = session.execute(
            text("SELECT * FROM users WHERE id = :val"),
            {"val": user_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    finally:
        session.close()

#........................

from datetime import datetime
import pytz

def register_user_with_class(
    session, numero_control, apellido_paterno, apellido_materno, nombres,
    username, password, rol, carrera, semestre, grupo, class_id
):
    if get_user_from_database(username):
        return False, "El usuario ya existe"

    password_hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    created_at = datetime.now(pytz.timezone("America/Mexico_City"))

    try:
        sql = text("""
        INSERT INTO users (username, email, password)
        VALUES (:username, :email, :password)
        """)

        db_session.execute(sql, {
            "username": username,
            "email": email,
            "password": password_hashed
        })

        session.commit()
        return True, "Usuario registrado correctamente"
    except Exception as e:
        session.rollback()
        return False, f"DB ERROR: {e}"

#------



app = Flask(__name__)
app.secret_key = 'tu_secreto_aqui'  # Para mensajes flash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        numero_control = request.form.get('numero_control')
        apellido_paterno = request.form.get('apellido_paterno')
        apellido_materno = request.form.get('apellido_materno')
        nombres = request.form.get('nombres')
        username = request.form.get('username')
        password = request.form.get('password')
        carrera = request.form.get('carrera')
        semestre = request.form.get('semestre')
        grupo = request.form.get('grupo')
        class_id = request.form.get('class_id')  # La clase a la que se asocia el usuario

        # Validar que la clase exista (opcional pero recomendado)
        session = get_db_session()
        clase = get_class_by_id(session, class_id)
        if not clase:
            flash("La clase seleccionada no existe.", "error")
            return render_template('register.html')

        created_at = datetime.now(pytz.timezone("America/Mexico_City"))

        # Registrar usuario
        success = register_user(
            session, numero_control, apellido_paterno, apellido_materno, nombres,
            username, password, carrera, semestre, grupo, created_at, class_id
        )

        if success:
            flash("Usuario registrado con éxito. Por favor haz login.", "success")
            return redirect(url_for('login'))
        else:
            flash("Error: Usuario o username ya existe.", "error")
            return render_template('register.html')

    # GET
    session = get_db_session()
    # Cargar todas las clases para mostrarlas en el formulario
    clases = session.execute("SELECT * FROM classes").fetchall()
    session.close()
    return render_template('register.html', clases=clases)


#-------------

#Cambios en la función register_user para #incluir class_id

def register_user(session, numero_control, apellido_paterno, apellido_materno, nombres, username, password, carrera, semestre, grupo, class_id, created_at):
    # Verificar si usuario existe
    existing_user = get_user_from_database(username)
    if existing_user:
        return False

    password_hashed = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        # Insertar usuario
        sql = text("""
            INSERT INTO users (numero_control, apellido_paterno, apellido_materno, nombres, username, password, carrera, semestre, grupo, created_at)
            VALUES (:numero_control, :apellido_paterno, :apellido_materno, :nombres, :username, :password, :carrera, :semestre, :grupo, :created_at)
        """)
        session.execute(sql, {
            "numero_control": numero_control,
            "apellido_paterno": apellido_paterno,
            "apellido_materno": apellido_materno,
            "nombres": nombres,
            "username": username,
            "password": password_hashed,
            "carrera": carrera,
            "semestre": semestre,
            "grupo": grupo,
            "created_at": created_at
        })
        session.commit()

        # Obtener el user_id generado
        user_id = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        # Insertar relación usuario - clase
        sql_rel = text("""
            INSERT INTO students_classes (user_id, class_id, grupo, created_at)
            VALUES (:user_id, :class_id, :grupo, :created_at)
        """)
        session.execute(sql_rel, {
            "user_id": user_id,
            "class_id": class_id,
            "grupo": grupo,
            "created_at": created_at
        })
        session.commit()

        return True

    except Exception as e:
        print(f"DB ERROR during user registration: {e}")
        session.rollback()
        return False


#-----------

#Método auxiliar para validar clase

def get_class_by_id(session, class_id):
    try:
        result = session.execute(
            text("SELECT * FROM classes WHERE id = :id"),
            {"id": class_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    except Exception as e:
        print(f"DB ERROR get_class_by_id: {e}")
        return None

# -----
def load_classes_for_user(user_id):
    session = get_db_session()
    try:
        # Clases donde el usuario es docente (docenteID en planes)
        docente_classes = session.execute(text("""
            SELECT DISTINCT c.id, c.name
            FROM classes c
            JOIN mat1 p ON p.class_id = c.id
            WHERE p.docenteID = :user_id
        """), {"user_id": user_id}).mappings().all()

        # Clases donde el usuario está inscrito como estudiante (students_classes)
        student_classes = session.execute(text("""
            SELECT DISTINCT c.id, c.name
            FROM classes c
            JOIN students_classes sc ON sc.class_id = c.id
            WHERE sc.user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        combined = {c['id']: c for c in (docente_classes + student_classes)}.values()
        return list(combined)
    finally:
        session.close()
#------------

def get_classes_for_user(user_id, rol):
    session = get_db_session()
    try:
        if rol == 'docente':
            result = session.execute(
                text("SELECT * FROM classes WHERE docente_id = :id"),
                {"id": user_id}
            )
        else:  # alumno
            result = session.execute(
                text("""
                    SELECT c.*
                    FROM class_students cs
                    JOIN classes c ON cs.class_id = c.id
                    WHERE cs.user_id = :id
                """),
                {"id": user_id}
            )
        classes = result.mappings().all()
        return [dict(row) for row in classes]
    finally:
        session.close()




