
import pytz
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session, send_file, make_response
from flask import session as flask_session
from flask_bcrypt import Bcrypt
from gevent import monkey; monkey.patch_all()
from gevent.pywsgi import WSGIServer
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
import tempfile
from weasyprint import HTML, CSS
import pymysql
from werkzeug.utils import secure_filename


from database import load_pg_from_db, load_pgn_from_db,  register_user, get_db_session, insert_actividad, load_plan_from_db, insert_plan,  load_pg_from_db2

from sqlalchemy import text



created_at = datetime.now()

def check_session_timeout():
    if 'username' in session:
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(minutes=60):
                session.clear()
                return False
        session['last_activity'] = datetime.now().isoformat()
        return True
    return False

"""
cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)
"""
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.permanent_session_lifetime = timedelta(minutes=60)


@app.route("/")
def hello_pm1():
        if not check_session_timeout():
            #flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
            return redirect(url_for('login'))

        pg = load_pg_from_db2()

        es_profesor = flask_session.get('es_profesor', False)
        username = flask_session.get('username', 'Invitado')
        

        return render_template('home.html', es_profesor=es_profesor , pg=pg, username=username)





#para extraer el contenido de la DB (cada pg) y mostralo en la página
@app.route('/pg/<int:pg_id>') 
def show_pg(pg_id):
    if not check_session_timeout():
        #flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
        return redirect(url_for('login'))

    # Supongamos que TEMAS es tu estructura de datos (lista o dict)
    pg = load_pg_from_db2()
    item = next((item for item in pg if item['plan'] == pg_id), None)
    if item is None:
        return "Not Found", 404
    return render_template('classpage.html', i=item)




#para extraer el contenido de la DB (cada plan) y mostralo en la página
@app.route('/plan/<int:id>', methods=['GET']) 
def show_plan(id):
    if not check_session_timeout():
        #flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
        return redirect(url_for('login'))

    show_form = request.method == "GET"
    

    # Supongamos que TEMAS es tu estructura de datos (lista o dict)
    plan = load_plan_from_db(id)
    #item = next((item for item in plan if item['cve'] == id), None)
    item = plan
    if item is None:
        return "Not Found", 404
    return render_template('plan.html', i=item, show_form=show_form)





#para jsonificar el contenido mostrado en la página
@app.route("/pgn/<int:id>")
def show_pgn(id):
    pgn = load_pgn_from_db(id)
    if pgn:
        return jsonify(pgn)
    else:
        return jsonify({'error': 'Not found'}), 404




#para que el usuario envíe una nueva actividad y registrarla en la DB
@app.route("/enviaractividad", methods=["GET", "POST"])
def enviaractividad():
    if not check_session_timeout():
        flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
        return redirect(url_for('login'))

    show_form = request.method == "POST"

    if request.method == "POST":
        try:
            actividad_num = request.form['actividad_num']
            numero_control = request.form['numero_control']
            pdf_file = request.files['pdf_file']

            if not pdf_file or not pdf_file.filename.endswith('.pdf'):
                flash("Debes subir un archivo PDF válido menor a 5MB.", "danger")
                return redirect(request.url)

            # Obtener la sesión de base de datos
            session_db = get_db_session()

            # Obtener datos del usuario
            query = text('SELECT * FROM users WHERE numero_control = :numero_control')
            user = session_db.execute(query, {'numero_control': numero_control}).mappings().first()

            if not user:
                flash("Número de control no encontrado en la base de datos.", "danger")
                return redirect(request.url)

            apellido_paterno = user['apellido_paterno']
            apellido_materno = user['apellido_materno']
            nombres = user['nombres']
            carrera = user['carrera']
            semestre = user['semestre']
            grupo = user['grupo']
            pdf_url = user['pdf_url']

            
            # Subir archivo a Cloudinary
            filename = secure_filename(f"actividad {apellido_paterno}_{apellido_materno}_{nombres}_{semestre}_{grupo}_{actividad_num}.pdf")
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type='raw',
                folder='actividades_pdf',
                public_id=filename
            )
            pdf_url = result.get('secure_url')
            print("✅ Carga en Cloudinary exitosa")

            # Establecer la fecha y hora actual en zona horaria de México
            created_at = datetime.now(pytz.timezone("America/Mexico_City"))

            # Insertar en la tabla actividades_inoc
            insert_actividad(
                session_db,
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
            print("✅ Inserción en DB exitosa")

            flash(f"Actividad {actividad_num} de {nombres} enviada correctamente.", "success")
            return redirect(url_for("hello_pm1"))

        except Exception as e:
            print("❌ Error during submission:", e)
            flash(f"Ocurrió un error al procesar la actividad {actividad_num}.", "danger")
            return redirect(url_for('enviaractividad'))

    return render_template("enviaractividad.html", show_form=show_form)



#para que el docente suba una planeación (anexo PDF de instrumentos) y registrarla en la DB
@app.route("/plan_carga", methods=["GET", "POST"])
def plan_carga():
    if not check_session_timeout():
        flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
        return redirect(url_for('login'))

    show_form = request.method == "POST"

    if request.method == "POST":
        try:
            print("📥 POST recibido")
            print("Campos en el formulario:", request.form.keys())
            plan = request.form['plan']
            asig = request.form['asig']
            meta = request.form['meta']
            prop = request.form['prop']
            temas = request.form['temas']
            plantel = request.form['plantel']
            ciclo = request.form['ciclo']
            periodo = request.form['periodo']
            carrera = request.form['carrera']
            semestre = request.form['semestre']
            grupos = request.form['grupos'].replace(",", "").replace(" ", "")
            horas_sem = request.form['horas_sem']
            docenteID = request.form['docenteID']
            imparte = request.form['imparte']
            parcial = request.form['parcial']
            trAsigP1 = request.form['trAsigP1']
            trtemaP1 = request.form['trtemaP1']
            trAsigP2 = request.form['trAsigP2']
            trtemaP2 = request.form['trtemaP2']
            trAsigP3 = request.form['trAsigP3']
            trtemaP3 = request.form['trtemaP3']
            trAsigP4 = request.form['trAsigP4']
            trtemaP4 = request.form['trtemaP4']
            trAsigM1 = request.form['trAsigM1']
            trtemaM1 = request.form['trtemaM1']
            trAsigM2 = request.form['trAsigM2']
            trtemaM2 = request.form['trtemaM2']
            trAsigM3 = request.form['trAsigM3']
            trtemaM3 = request.form['trtemaM3']
            trAsigM4 = request.form['trAsigM4']
            trtemaM4 = request.form['trtemaM4']
            apDur = request.form['apDur']
            apEv = request.form['apEv']
            apIns = request.form['apIns']
            apPond = request.form['apPond']
            apAct = request.form['apAct']
            deDur = request.form['deDur']
            deEv = request.form['deEv']
            deIns = request.form['deIns']
            dePond = request.form['dePond']
            deAct = request.form['deAct']
            ciDur = request.form['ciDur']
            ciEv = request.form['ciEv']
            ciIns = request.form['ciIns']
            ciPond = request.form['ciPond']
            ciAct = request.form['ciAct']
            materiales = request.form['materiales']
            equipo = request.form['equipo']
            fuentes = request.form['fuentes']
            elabora = request.form['elabora']
            revisa = request.form['revisa']
            avala = request.form['avala']
            cve = f"{docenteID}_{ciclo}_{periodo}_{semestre}_{grupos}_{asig}_{plan}"
            pdf_file = request.files['pdf_file']
            parPond = request.form['parPond']
            


            print("📋 Datos del formulario extraídos correctamente")

            if not pdf_file or not pdf_file.filename.endswith('.pdf'):
                flash("Debes subir un archivo PDF válido menor a 5MB.", "danger")
                return redirect(request.url)

            # Obtener la sesión de base de datos
            session_db = get_db_session()

            # Obtener datos del usuario
            #query = text('SELECT * FROM users WHERE numero_control = :numero_control')
            #user = session_db.execute(query, {'numero_control': numero_control}).mappings().first()

            #if not user:
            #    flash("Registro no encontrada en la base de datos.", "danger")
            #    return redirect(request.url)


            # Subir archivo a Cloudinary
            print("☁️ Subiendo archivo a Cloudinary...")
            filename = secure_filename(f"Plan {plan}_{cve}.pdf")
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type='raw',
                folder='instrumentos_pdf',
                public_id=filename
            )
            pdf_url = result.get('secure_url')
            print("✅ Carga en Cloudinary exitosa")

            # Establecer la fecha y hora actual en zona horaria de México
            created_at = datetime.now(pytz.timezone("America/Mexico_City"))

            # Insertar en la tabla planInocAgro
            print("📝 Insertando en base de datos...")
            new_plan_id=insert_plan(
                session_db,
                plan,
                asig,
                meta,
                prop,
                temas,
                plantel,
                ciclo,
                periodo,
                carrera,
                semestre,
                grupos,
                horas_sem,
                docenteID, 
                imparte,
                parcial,
                trAsigP1,
                trtemaP1,
                trAsigP2,
                trtemaP2,
                trAsigP3,
                trtemaP3,
                trAsigP4,
                trtemaP4,
                trAsigM1,
                trtemaM1,
                trAsigM2,
                trtemaM2,
                trAsigM3,
                trtemaM3,
                trAsigM4,
                trtemaM4,
                apDur,
                apEv,
                apIns,
                apPond,
                apAct,
                deDur,
                deEv,
                deIns,
                dePond,
                deAct,
                ciDur,
                ciEv,
                ciIns,
                ciPond,
                ciAct,
                materiales,
                equipo,
                fuentes,
                elabora,
                revisa,
                avala,
                cve,
                created_at,
                pdf_url,
                parPond
                
            )
            print("✅ Inserción en DB exitosa")

            flash(f"Planeación {cve} de {docenteID} enviada correctamente.", "success")
            return redirect(url_for("show_plan", id=new_plan_id))

        except pymysql.err.IntegrityError as e:
            if "1062" in str(e):  # Duplicate entry error
                with connection.cursor() as cursor:
                    cursor.execute(update_query, data)
                connection.commit()
                return "Plan updated successfully"

        except pymysql.MySQLError as e:
            print("❌ Error MySQL:", e)
            flash("Error al acceder a la base de datos.", "danger")
            return redirect(url_for('plan_carga'))

        
        except Exception as e:
            print("❌ Error during submission:", e)
            flash(f"Ocurrió un error al procesar la planeación {cve}.", "danger")
            return redirect(url_for('plan_carga'))

    return render_template("plan_carga.html", show_form=show_form)

"""
#para registrar un nuevo usuario y almacenarlo en la DB
@app.route("/register", methods=["GET", "POST"])
def register():
    choice = request.form.get('choice') #or request.args.get('choice')

    if request.method == "POST":
        try:
            # Extract data from the form
            numero_control = request.form['numero_control']
            apellido_paterno = request.form['apellido_paterno']
            apellido_materno = request.form['apellido_materno']
            nombres = request.form['nombres']
            username = request.form['username']
            password = request.form['password']
            carrera = request.form['carrera']
            semestre = request.form['semestre']
            grupo = request.form['grupo']


            # Validate password (you can extend this validation)
            if len(password) < 8:
                flash("La contraseña debe tener al menos 8 caracteres.", "danger")
                return render_template("register.html", choice=choice)
                

                # Initialize DB session
            db_session = get_db_session()
            created_at = datetime.now(pytz.timezone("America/Mexico_City"))

            if not register_user(db_session, numero_control, apellido_paterno, apellido_materno, nombres, username, password, carrera, semestre, grupo):
                flash("Ese nombre de usuario ya está registrado. Por favor, elige otro.", "danger")
                return render_template("register.html", choice=choice)

            # Call the function to register the user (make sure it handles the db insertion)
            db_session = get_db_session()
            created_at = datetime.now(pytz.timezone("America/Mexico_City"))
            register_user(db_session, numero_control, apellido_paterno, apellido_materno, nombres, username, password, carrera, semestre, grupo)
            db_session.close()

            flash(f"Registro exitoso para {nombres}!", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print(f"Error en el registro: {e}")
            flash("Hubo un problema al registrarte. Intenta nuevamente.", "danger")
            return render_template("register.html", choice=choice)

    return render_template("register.html", choice=choice)
"""

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        if user_type == 'A':
            return redirect(url_for('register_alumno'))
        elif user_type == 'D':
            return redirect(url_for('register_docente'))
        else:
            flash("Seleccione un tipo de usuario válido.")
    return render_template('select_register_type.html')


def handle_register_user(choice):
    template_map = {
            "A": "register_alumno.html",
            "D": "register_docente.html"
        }

    template = template_map.get(choice)

    if not template:
            flash("Tipo de usuario no válido.", "danger")
            return redirect(url_for("home"))
    
    db_session = None  #

    if request.method == "POST":
        try:
            # Get form data (use .get() to avoid KeyError if field is missing)
            numero_control = request.form.get('numero_control', '').strip()
            apellido_paterno = request.form.get('apellido_paterno', '').strip()
            apellido_materno = request.form.get('apellido_materno', '').strip()
            nombres = request.form.get('nombres', '').strip()
            username = request.form.get('username', '').strip()
            #password = request.form.get('password', '')
            carrera = request.form.get('carrera', '').strip()
            semestre = request.form.get('semestre', '').strip()
            grupo = request.form.get('grupo', '').strip()

            # Simple validation
            password_raw = request.form.get('password', '') #secure validation
            if len(password_raw) < 8: #
                flash("La contraseña debe tener al menos 8 caracteres.", "danger")
                return render_template(template)
            password = bcrypt.generate_password_hash(password_raw).decode('utf-8')#secure password

            db_session = get_db_session()
            created_at = datetime.now(pytz.timezone("America/Mexico_City"))

            # ✅ Check if the username is already taken
            existing_user = db_session.execute(
                text("SELECT 1 FROM users WHERE username = :username"),
                {"username": username}
            ).fetchone()

            if existing_user:
                flash("Ese nombre de usuario ya está registrado. Por favor, elige otro.", "danger")
                return render_template(template)

            success = register_user(
                db_session,
                numero_control,
                apellido_paterno,
                apellido_materno,
                nombres,
                username,
                password,
                carrera,
                semestre,
                grupo,
                created_at
            )

            if not success:
                flash("Ese nombre de usuario ya está registrado. Por favor, elige otro.", "danger")
                return render_template(template)

            flash(f"Registro exitoso para {nombres}!", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print(f"Error en el registro: {e}")
            flash("Hubo un problema al registrarte. Intenta nuevamente.", "danger")
            return render_template(template)

        finally:
            if db_session:  # ✅ Only close if it exists
                db_session.close()

    # GET method: show registration form
    return render_template(template)




@app.route("/register/alumno", methods=["GET", "POST"])
def register_alumno():
    return handle_register_user(choice="A")

@app.route("/register/docente", methods=["GET", "POST"])
def register_docente():
    return handle_register_user(choice="D")



@app.route("/plan/<int:plan_id>/edit", methods=["GET"])
def edit_plan(plan_id):
    db = get_db_session()
    plan = db.query(Plan).filter_by(id=plan_id).first()

    if not plan:
        return "Plan not found", 404

    return render_template("edit_plan.html", plan=plan)



"""
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Trying login for user: {username}")
        try:
            # Connect to the database and fetch user data by username
            db_session = get_db_session()
            query = text('SELECT * FROM users WHERE username = :username')
            result = db_session.execute(query, {'username': username})
            user = result.mappings().first()
            db_session.close()

            if user:
                # ✅ Secure password check using Bcrypt
                if bcrypt.check_password_hash(user['password'], password):
                    print("User found:", user)
                # Check if password matches (you should hash passwords in production)
                #if user['password'] == password:
                #    print("Password correct")
                    flask_session.permanent = True
                    flask_session['username'] = username
                    flask_session['last_activity'] = datetime.now().isoformat()

                    #  --- Lógica añadida para determinar tipo de usuario ---
                    school_id = user.get('numero_control', '')
                    es_profesor = len(school_id) >= 4 and school_id[5].isalpha()
                    flask_session['es_profesor'] = es_profesor
                    
                    flash(f'{username} inició sesión correctamente', 'success')


                    
                    return redirect(url_for('hello_pm1'))  
                    # Redirect on success
                else:
                    print("Password incorrect")
                    flash('Contraseña equivocada. Intente de nuevo.', 'danger')
                    return render_template('login.html')
            else:
                flash('Nombre de usuario no existe. Intente de nuevo.', 'danger')
                return render_template('login.html')

        except Exception as e:
            print("Exception during login:", e)
            flash('Ocurrió un error. Intente más tarde.', 'danger')
            return render_template('login.html')

    return render_template('login.html')
"""
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_from_database(username)

        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user.get('role', 'student')  # 'docente' o 'estudiante'

            return redirect('/dashboard')
        else:
            flash("Usuario o contraseña incorrectos.")
            return redirect('/login')

    return render_template('login.html')
    #-----


@app.route('/select_class')
def select_class():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    rol = session['rol']

    classes = get_classes_for_user(user_id, rol)
    return render_template('select_class.html', classes=classes)


@app.route('/class_dashboard')
def class_dashboard():
    if 'current_class_id' not in session:
        return redirect(url_for('select_class'))

    class_id = session['current_class_id']
    # Aquí podrías cargar actividades, planeaciones, etc.
    return render_template('class_dashboard.html', class_id=class_id)

    #----
@app.route('/enter_class', methods=['POST'])
def enter_class():
    class_id = request.form.get('class_id')
    session['current_class_id'] = class_id
    return redirect(url_for('class_dashboard'))

#-------
@app.route('/submit_activity', methods=['GET', 'POST'])
def submit_activity():
    if 'user_id' not in session or 'current_class_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        actividad_num = request.form.get('actividad_num')
        pdf_url = request.form.get('pdf_url')  # en producción sería `request.files`
        created_at = datetime.now(pytz.timezone("America/Mexico_City"))

        user_id = session['user_id']
        class_id = session['current_class_id']

        # Carga datos del usuario
        user = get_user_by_id(user_id)

        success = insert_actividad(
            session=get_db_session(),
            actividad_num=actividad_num,
            apellido_paterno=user['apellido_paterno'],
            apellido_materno=user['apellido_materno'],
            nombres=user['nombres'],
            carrera=user['carrera'],
            semestre=user['semestre'],
            grupo=user['grupo'],
            pdf_url=pdf_url,
            created_at=created_at,
            user_id=user_id,
            class_id=class_id
        )

        if success:
            return "✅ Actividad enviada correctamente"
        else:
            return "❌ Error al enviar la actividad"

    return render_template('submit_activity.html')
#----

@app.route('/ver_actividades')
def ver_actividades():
    if 'user_id' not in session or 'current_class_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    class_id = session['current_class_id']

    # Obtener información del usuario para saber si es docente o estudiante
    user = get_user_by_id(user_id)

    session_db = get_db_session()

    try:
        if user['rol'] == 'docente':
            # Ver todas las actividades de esa clase
            result = session_db.execute(text("""
                SELECT * FROM actividades_inoc
                WHERE class_id = :class_id
                ORDER BY created_at DESC
            """), {"class_id": class_id})
        else:
            # Ver solo las actividades del estudiante
            result = session_db.execute(text("""
                SELECT * FROM actividades_inoc
                WHERE class_id = :class_id AND user_id = :user_id
                ORDER BY created_at DESC
            """), {"class_id": class_id, "user_id": user_id})

        actividades = result.mappings().all()
        return render_template('ver_actividades.html', actividades=actividades, user=user)

    except Exception as e:
        print(f"DB ERROR: {e}")
        return "Error al cargar las actividades"
    finally:
        session_db.close()

#----
@app.route('/ver_actividades', methods=['GET', 'POST'])
def ver_actividades():
    if 'user_id' not in session or 'current_class_id' not in session:
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])
    class_id = session['current_class_id']
    filtros = {}
    actividad_num = request.form.get("actividad_num")
    if actividad_num:
        filtros["actividad_num"] = actividad_num

    session_db = get_db_session()
    query = text("""
        SELECT * FROM actividades_inoc
        WHERE class_id = :class_id
        {filter_clause}
        ORDER BY created_at DESC
    """.format(filter_clause=" AND actividad_num = :actividad_num" if actividad_num else ""))

    params = {"class_id": class_id}
    if actividad_num:
        params["actividad_num"] = actividad_num

    if user['rol'] == 'alumno':
        query = text(str(query) + " AND user_id = :user_id")
        params["user_id"] = session['user_id']

    result = session_db.execute(query, params).mappings().all()
    
    session_db.close()

    
    return render_template('ver_actividades.html', actividades=result, user=user)

#------------
#Permitir a docentes crear y editar clases.

@app.route('/mis_clases')
def mis_clases():
    if session.get('rol') != 'docente':
        return redirect(url_for('login'))
    clases = get_classes_for_user(session['user_id'], 'docente')
    return render_template('mis_clases.html', clases=clases)

@app.route('/crear_clase', methods=['GET', 'POST'])
def crear_clase():
    if session.get('rol') != 'docente':
        return redirect(url_for('login'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        grupo = request.form['grupo']
        session_db = get_db_session()
        session_db.execute(text("""
            INSERT INTO classes (name, description, docente_id)
            VALUES (:name, :desc, :doc)
        """), {"name": nombre, "desc": grupo, "doc": session['user_id']})
        session_db.commit()
        session_db.close()
        return redirect(url_for('mis_clases'))
    return render_template('crear_clase.html')

#------
@app.route('/dashboard_clase')
def dashboard_clase():
    class_id = session.get('current_class_id')
    if not class_id:
        return redirect(url_for('select_class'))

    session_db = get_db_session()
    total = session_db.execute(text("SELECT COUNT(*) FROM actividades_inoc WHERE class_id = :cid"), {"cid": class_id}).scalar()
    calificadas = session_db.execute(text("SELECT COUNT(*) FROM actividades_inoc WHERE class_id = :cid AND calificacion IS NOT NULL"), {"cid": class_id}).scalar()
    promedio = session_db.execute(text("SELECT AVG(calificacion) FROM actividades_inoc WHERE class_id = :cid AND calificacion IS NOT NULL"), {"cid": class_id}).scalar()
    session_db.close()

    return render_template('dashboard_clase.html', total=total, calificadas=calificadas, promedio=promedio)
#---------

from datetime import date
@app.route('/asistencia', methods=['GET', 'POST'])
def asistencia():
    if 'user_id' not in session or 'current_class_id' not in session:
        return redirect(url_for('login'))

    class_id = session['current_class_id']
    session_db = get_db_session()
    estudiantes = session_db.execute(text("""
        SELECT u.id, u.nombres, u.apellido_paterno
        FROM users u
        JOIN students_classes sc ON sc.user_id = u.id
        WHERE sc.class_id = :cid
    """), {"cid": class_id}).mappings().all()

    # Selección del período
    periodo = request.form.get('periodo', 'A')
    if periodo == 'A':
        start, end = date(2025,9,8), date(2025,10,3)
    elif periodo == 'B':
        start, end = date(2025,10,6), date(2025,11,4)
    else:
        start, end = date(2025,11,5), date(2026,1,15)

    # Generar lista de fechas en el período
    fechas = [start + timedelta(days=i) for i in range((end-start).days + 1)]

    if request.method == 'POST' and 'guardar' in request.form:
        for uid in request.form.getlist('user'):
            fch = request.form.get('fecha')
            presente = 1 if request.form.get(f"check_{uid}_{fch}") == 'on' else 0
            session_db.execute(text("""
                INSERT INTO asistencia (user_id, class_id, fecha, presente)
                VALUES (:uid, :cid, :fch, :pres)
                ON DUPLICATE KEY UPDATE presente = :pres
            """), {"uid": uid, "cid": class_id, "fch": fch, "pres": presente})
        session_db.commit()

    # Cargar registros existentes
    registros = session_db.execute(text("""
        SELECT user_id, fecha, presente
        FROM asistencia
        WHERE class_id = :cid AND fecha BETWEEN :start AND :end
    """), {"cid": class_id, "start": start, "end": end}).mappings().all()
    session_db.close()

    return render_template('asistencia.html', estudiantes=estudiantes, fechas=fechas, registros=registros, periodo=periodo)
#-----------

from flask import request, session, redirect, url_for, render_template
from database import get_db_session, get_user_by_id
from datetime import date, timedelta
from sqlalchemy import text

@app.route('/dashboard_asistencia', methods=['GET'])
def dashboard_asistencia():
    if 'user_id' not in session or 'current_class_id' not in session:
        return redirect(url_for('login'))

    class_id = session['current_class_id']
    user = get_user_by_id(session['user_id'])
    if user['rol'] != 'docente':
        return "Acceso denegado: solo docentes pueden ver este dashboard", 403

    # Selección de período (por GET query param o default 'A')
    periodo = request.args.get('periodo', 'A')
    if periodo == 'A':
        start, end = date(2025,9,8), date(2025,10,3)
    elif periodo == 'B':
        start, end = date(2025,10,6), date(2025,11,4)
    else:
        start, end = date(2025,11,5), date(2026,1,15)

    total_days = (end - start).days + 1

    session_db = get_db_session()

    # Obtener lista de estudiantes de la clase
    estudiantes = session_db.execute(text("""
        SELECT u.id, u.nombres, u.apellido_paterno
        FROM users u
        JOIN students_classes sc ON sc.user_id = u.id
        WHERE sc.class_id = :cid
    """), {"cid": class_id}).mappings().all()

    # Obtener registros de asistencia del período
    asistencias = session_db.execute(text("""
        SELECT user_id, COUNT(*) AS asistencias
        FROM asistencia
        WHERE class_id = :cid AND fecha BETWEEN :start AND :end AND presente = 1
        GROUP BY user_id
    """), {"cid": class_id, "start": start, "end": end}).mappings().all()

    # Convertir a diccionario { user_id: asistencias }
    asist_dict = {a['user_id']: a['asistencias'] for a in asistencias}

    if asistencias:
        max_asist = max(asist_dict.values())
    else:
        max_asist = 0

    # Construir resumen por estudiante
    resumen = []
    for est in estudiantes:
        uid = est['id']
        cnt = asist_dict.get(uid, 0)
        porcentaje = (cnt / max_asist * 100) if max_asist > 0 else 0
        resumen.append({
            "id": uid,
            "nombre": f"{est['nombres']} {est['apellido_paterno']}",
            "asistencias": cnt,
            "porcentaje": round(porcentaje, 2)
        })

    session_db.close()

    return render_template(
        'dashboard_asistencia.html',
        resumen=resumen,
        total_days=total_days,
        periodo=periodo
    )
    
#-----

#-----
@app.route('/calificar/<int:actividad_id>', methods=['POST'])
def calificar_actividad(actividad_id):
    if 'user_id' not in session or 'current_class_id' not in session:
        return redirect(url_for('login'))

    calificacion = request.form.get('calificacion')
    comentario = request.form.get('comentario')
    session_db = get_db_session()
    # Opcionalmente valida rol docente
    session_db.execute(text("""
        UPDATE actividades_inoc
        SET calificacion = :cal, comentario = :com
        WHERE id = :id AND class_id = :class_id
    """), {"cal": calificacion, "com": comentario, "id": actividad_id, "class_id": session['current_class_id']})
    session_db.commit()
    session_db.close()
    return redirect(url_for('ver_actividades'))


#-----

def load_classes_for_user(user_id):
    session = get_db_session()
    try:
        # Traer clases donde es docente
        docente_classes = session.execute(text("""
            SELECT DISTINCT c.id, c.name 
            FROM classes c 
            JOIN plans p ON p.class_id = c.id
            WHERE p.docenteID = :user_id
        """), {"user_id": user_id}).mappings().all()

        # Traer clases donde es estudiante
        student_classes = session.execute(text("""
            SELECT DISTINCT c.id, c.name
            FROM classes c
            JOIN students_classes sc ON sc.class_id = c.id
            WHERE sc.user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        # Unir sin duplicados
        combined = {c['id']: c for c in (docente_classes + student_classes)}.values()
        return list(combined)
    finally:
        session.close()
#------




@app.route('/download_pdf/<int:id>')
def download_pdf(id):
    plan = load_plan_from_db(id)
    if not plan:
        return "Plan not found", 404

    # Render HTML from template
    rendered = render_template('plan_pdf.html', i=plan)

    # Define CSS for tabloid size and landscape orientation
    css = CSS(string='''
        @page {
            size: 17in 11in;
            margin: 1cm;
        }
    ''')

    # Generate PDF from HTML
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        HTML(string=rendered).write_pdf(tmpfile.name, stylesheets=[css])
        tmpfile.seek(0)
        return send_file(tmpfile.name, as_attachment=True, download_name=f"plan_{id}.pdf")



#@app.route('/choice', methods=['GET', 'POST'])
#def handle_choice():
#    opciones = None
#    if request.method == 'POST':
#        opciones = request.form.get('choice')  # 'value1' or 'value2' or None
#    return render_template('register.html', opciones=opciones)

from flask import Flask, render_template, request, redirect, session, url_for, flash
from database import get_user_from_database, get_user_classes





@app.route('/logout')
def logout():
    
    session.pop('username', None)
    
    return redirect(url_for('login'))


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()