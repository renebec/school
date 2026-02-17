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

from database import load_pg_from_db, load_pgn_from_db,  register_user, get_db_session, insert_actividad, load_plan_from_db, insert_plan,  load_pg_from_db2, is_preregistered, load_all_pdfs, load_user_pdfs

from sqlalchemy import text

created_at = datetime.now()

import time

def check_session_timeout():
    last = session.get('last_activity')
    if not last:
        return False

    now = time.time()
    timeout_seconds = 60 * 60  # 60 minutes

    # If last_activity is not a float (old ISO string), reset session
    try:
        last = float(last)
    except:
        session.clear()
        return False

    if now - last > timeout_seconds:
        session.clear()
        return False

    # Refresh timestamp
    session['last_activity'] = time.time()
    return True

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
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25 MB
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.permanent_session_lifetime = timedelta(minutes=60)


@app.route("/")
def hello_pm1():
    # 1. Validar expiración de sesión
    if not check_session_timeout():
        flash("Su sesión ha expirado. Por favor, inicie sesión nuevamente.", "danger")
        return redirect(url_for("login"))

    # 2. Obtener datos del usuario desde session
    username = session.get("username")
    numero_control = session.get("numero_control")
    es_profesor = session.get("es_profesor", False)
    asig = session.get("asig")
    
    # Validar que haya sesión
    if not username:
        flash("Debe iniciar sesión.", "danger")
        return redirect(url_for("login"))

    # 3. Conexión a DB
    session_db = get_db_session()

    try:
        # 4. Cargar PDFs según el tipo de usuario
        if es_profesor:
            pg = load_pg_from_db2(asig)
            pdfs = load_all_pdfs(session_db, asig)
        else:
            pg = load_pg_from_db2(asig)
            pdfs = load_user_pdfs(session_db, numero_control, asig)

    except Exception as e:
        print("❌ Error al cargar PDFs:", e)
        flash("Error al cargar los archivos.", "danger")
        pdfs = []
    finally:
        session_db.close()


    print("ASIG en sesión:", asig)

    for fila in pg:
        print(fila['asig'], fila['parcial'])

    # 5. Renderizar plantilla
    return render_template(
        "home.html",
        es_profesor=es_profesor,
        username=username,
        numero_control=numero_control,
        pdfs=pdfs,
        pg=pg

    )

    





#para extraer el contenido de la DB (cada pg) y mostralo en la página
@app.route('/pg/<int:pg_id>') 
def show_pg(pg_id):
    if not check_session_timeout():
        #flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
        return redirect(url_for('login'))

    # Supongamos que TEMAS es tu estructura de datos (lista o dict)
    pg = load_pg_from_db()
    item = next((item for item in pg if item['plan'] == pg_id), None)
    if item is None:
        return "Not Found", 404
    session['asignatura_actual'] = item['asig']
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



@app.route("/enviaractividad", methods=["GET", "POST"])
def enviaractividad():
    if not check_session_timeout():
        flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
        return redirect(url_for('login'))

    asig = session.get('asig')
    if not asig:
        flash("No se puede enviar la actividad porque no hay asignatura seleccionada.", "danger")
        return redirect(url_for('hello_pm1'))

    if request.method == "GET":
        return render_template("enviaractividad.html", show_form=True, asignatura=asig)

    try:
        # --- Recibir datos ---

        numero_control = request.form.get("numero_control")
        actividad_num = request.form.get("actividad_num")
        pdf_file = request.files.get("pdf_file")

        # --- Validaciones ---
        if not numero_control or not pdf_file or not actividad_num:
            flash("Debes ingresar número de control, seleccionar número de actividad y subir un PDF.", "danger")
            return redirect(url_for("enviaractividad"))

        if not pdf_file.filename.lower().endswith(".pdf"):
            flash("El archivo debe ser un PDF.", "danger")
            return redirect(url_for("enviaractividad"))

        # Validar tamaño (máx 10 MB)
        pdf_bytes = pdf_file.read()
        if len(pdf_bytes) > 10 * 1024 * 1024:
            flash("El PDF debe ser menor o igual a 10 MB.", "danger")
            return redirect(url_for("enviaractividad"))

        # Regresar puntero al inicio
        pdf_file.seek(0)

        # --- Conexión a la BD ---
        session_db = get_db_session()

        try:
            # Obtener datos completos del usuario
            query = text("""
                SELECT numero_control, nombres, apellido_paterno, apellido_materno,
                       carrera, semestre, grupo
                FROM users
                WHERE numero_control = :nc
            """)

            user = session_db.execute(query, {"nc": numero_control}).mappings().first()

            if not user:
                flash("Número de control no encontrado en la base de usuarios.", "danger")
                return redirect(url_for("enviaractividad"))

            # --- Generar nombre único ---
            base_name = f"actividad_{user['carrera']}_{user['numero_control']}{user['apellido_paterno']}_{user['apellido_materno']}_{user['nombres']}{actividad_num}"
            base_name = secure_filename(base_name)
            filename = f"{base_name}_{int(time.time())}.pdf"

            # --- Subir PDF a Cloudinary ---
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type="raw",
                folder="actividades_pdf",
                public_id=filename,
                unique_filename=False,
                overwrite=True
            )

            # --- URL segura para abrir en otra pestaña ---
            pdf_url = result.get("secure_url")  # ✅ Esta URL se abre directamente en el navegador

            # --- Insertar en la tabla actividades ---
            created_at = datetime.now(pytz.timezone("America/Mexico_City"))

            insert_actividad(
                session_db,
                numero_control,                 # 1
                actividad_num,                  # 2
                user["apellido_paterno"],       # 3
                user["apellido_materno"],       # 4
                user["nombres"],                # 5
                user["carrera"],                # 6
                user["semestre"],               # 7
                user["grupo"],                  # 8
                pdf_url,
                asig,# 9
                created_at                      # 10
            )
            
            session_db.commit()

        except Exception as db_err:
            session_db.rollback()

            # Si el PDF ya se subió pero hubo error en DB → eliminar
            try:
                cloudinary.uploader.destroy(f"actividades_pdf/{filename}", resource_type="raw")
            except:
                pass

            print("❌ Error en DB:", db_err)
            flash("Ocurrió un error al registrar la actividad en la base de datos.", "danger")
            return redirect(url_for("enviaractividad"))

        finally:
            session_db.close()

        flash(f"PDF de {user['nombres']} {user['apellido_paterno']} enviado correctamente.", "success")
        return redirect(url_for("hello_pm1"))

    except Exception as e:
        print("❌ Error general:", e)
        flash("Ocurrió un error inesperado al procesar el registro.", "danger")
        return redirect(url_for("enviaractividad"))


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
            return redirect(url_for("hello_pm1"))

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


            # Format check: validate user type based on numero_control
            is_teacher_form = (choice == "D")
            fourth_char = numero_control[2] if len(numero_control) >= 4 else None

            if is_teacher_form and (not fourth_char or not fourth_char.isalpha()):
                flash("El número de control No corresponde a un docente.", "danger")
                return render_template(template)

            if not is_teacher_form and fourth_char and fourth_char.isalpha():
                flash("El número de control corresponde a un docente. Selecciona 'Docente' para registrarte.", "danger")
                return render_template(template)

            if not is_preregistered(numero_control):
                flash("No se reconoce ese número de control; imposible registrar.", "danger")
                return render_template(template)


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
            flash("Hubo un problema al registrarte. Inténtelo más tarde.", "danger")
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



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        asig = request.form['asig']
        print(f"Trying login for user: {username}")

        try:
            # Conexión a la DB
            db_session = get_db_session()
            query = text('SELECT * FROM users WHERE username = :username')
            result = db_session.execute(query, {'username': username})
            user = result.mappings().first()
            db_session.close()

            if not user:
                flash('Nombre de usuario no existe. Intente de nuevo.', 'danger')
                return render_template('login.html')

            # Verificar contraseña
            if not bcrypt.check_password_hash(user['password'], password):
                flash('Contraseña equivocada. Intente de nuevo.', 'danger')
                return render_template('login.html')

            # Login exitoso
            print("User found:", user)
            session.permanent = True
            session['username'] = user['username']
            session['numero_control'] = user['numero_control']   # ← FALTABA ESTO
            session["asig"] = asig
            session['last_activity'] = time.time()

            # Detectar profesor (si el 4to caracter es letra)
            nc = user['numero_control']
            session['es_profesor'] = len(nc) >= 4 and nc[3].isalpha()

            flash(f'{username} inició sesión correctamente', 'success')
            return redirect(url_for('hello_pm1'))

        except Exception as e:
            print("Exception during login:", e)
            flash('Ocurrió un error. Intente más tarde.', 'danger')
            return render_template('login.html')

    return render_template('login.html')




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





@app.route('/logout')
def logout():
    session.clear()  # removes everything from session
    flash("Has cerrado sesión correctamente.", "success")
    return redirect(url_for('login'))