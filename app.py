import pytz
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask import session as flask_session
from gevent import monkey; monkey.patch_all()
from gevent.pywsgi import WSGIServer
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader

from database import load_pg_from_db, load_pgn_from_db,  register_user, get_db_session, insert_actividad, load_plan_from_db, insert_plan

from sqlalchemy import text

created_at = datetime.now()

def check_session_timeout():
    if 'username' in session:
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(minutes=30):
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
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.permanent_session_lifetime = timedelta(minutes=20)


@app.route("/")
def hello_pm1():
        if not check_session_timeout():
            #flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
            return redirect(url_for('login'))

        pg = load_pg_from_db()
        

        return render_template('home.html', pg=pg)





#para extraer el contenido de la DB (cada pg) y mostralo en la página
@app.route('/pg/<int:pg_id>') 
def show_pg(pg_id):
    if not check_session_timeout():
        #flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
        return redirect(url_for('login'))

    # Supongamos que TEMAS es tu estructura de datos (lista o dict)
    pg = load_pg_from_db()
    item = next((item for item in pg if item['id'] == pg_id), None)
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
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type='raw',
                folder='actividades_pdf'
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
            asig = request.form['asig']
            prop = request.form['prop']
            temas = request.files['temas']
            plantel = request.files['plantel']
            ciclo = request.files['ciclo']
            periodo = request.files['periodo']
            carrera = request.files['carrera']
            semestre = request.files['semestre']
            grupos = request.files['grupos']
            horas_sem = request.files['horas_sem']
            docenteID = request.files['docenteID']
            imparte = request.files['imparte']
            trAsig1 = request.files['trAsig1']
            trtema1 = request.files['trtema1']
            trAsig2 = request.files['trAsig2']
            trtema2 = request.files['trtema2']
            trAsig3 = request.files['trAsig3']
            trtema3 = request.files['trtema3']
            apDur = request.files['apDur']
            apEv = request.files['apEv']
            apIns = request.files['apIns']
            apPond = request.files['apPond']
            apAct = request.files['apAct']
            deDur = request.files['deDur']
            deEv = request.files['deEv']
            deIns = request.files['deIns']
            dePond = request.files['dePond']
            deAct = request.files['deAct']
            ciDur = request.files['ciDur']
            ciEv = request.files['ciEv']
            ciIns = request.files['ciIns']
            ciPond = request.files['ciPond']
            ciAct = request.files['ciAct']
            materiales = request.files['materiales']
            equipo = request.files['equipo']
            fuentes = request.files['fuentes']
            elabora = request.files['elabora']
            revisa = request.files['revisa']
            avala = request.files['avala']
            cve = request.files['cve']
            created_at = request.files['created_at']
            pdf_url = request.files['pdf_url']

            if not pdf_file or not pdf_file.filename.endswith('.pdf'):
                flash("Debes subir un archivo PDF válido menor a 5MB.", "danger")
                return redirect(request.url)

            # Obtener la sesión de base de datos
            session_db = get_db_session()

            # Obtener datos del usuario
            query = text('SELECT * FROM planInocAgro WHERE cve = :cve')
            user = session_db.execute(query, {'cve': cve}).mappings().first()

            if not user:
                flash("Registro no encontrada en la base de datos.", "danger")
                return redirect(request.url)

            asig = user['asig']
            prop = user['prop']
            temas = user['temas']
            plantel = user['plantel']
            ciclo = user['ciclo']
            periodo = user['periodo']
            carrera = user['carrera']
            semestre = user['semestre']
            grupos = user['grupos']
            horas_sem = user['horas_sem']
            docenteID = user['docenteID']
            imparte = user['imparte']
            trAsig1 = user['trAsig1']
            trtema1 = user['trtema1']
            trAsig2 = user['trAsig2']
            trtema2 = user['trtema2']
            trAsig3 = user['trAsig3']
            trtema3 = user['trtema3']
            apDur = user['apDur']
            apEv = user['apEv']
            apIns = user['apIns']
            apPond = user['apPond']
            apAct = user['apAct']
            deDur = user['deDur']
            deEv = user['deEv']
            deIns = user['deIns']
            dePond = user['dePond']
            deAct = user['deAct']
            ciDur = user['ciDur']
            ciEv = user['ciEv']
            ciIns = user['ciIns']
            ciPond = user['ciPond']
            ciAct = user['ciAct']
            materiales = user['materiales']
            equipo = user['equipo']
            fuentes = user['fuentes']
            elabora = user['elabora']
            revisa = user['revisa']
            avala = user['avala']
            cve = user['cve']
            created_at = user['created_at']
            pdf_url = user['pdf_url']

            # Subir archivo a Cloudinary
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type='raw',
                folder='instrumentos_pdf'
            )
            pdf_url = result.get('secure_url')
            print("✅ Carga en Cloudinary exitosa")

            # Establecer la fecha y hora actual en zona horaria de México
            created_at = datetime.now(pytz.timezone("America/Mexico_City"))

            # Insertar en la tabla planInocAgro
            insert_plan(
                asig,
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
                trAsig1,
                trtema1,
                trAsig2,
                trtema2,
                trAsig3,
                trtema3,
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
                pdf_url
            )
            print("✅ Inserción en DB exitosa")

            flash(f"Planeación {cve} de {docenteID} enviada correctamente.", "success")
            return redirect(url_for("hello_pm1"))

        except Exception as e:
            print("❌ Error during submission:", e)
            flash(f"Ocurrió un error al procesar la planeación {cve}.", "danger")
            return redirect(url_for('plan_carga'))

    return render_template("plan_carga.html", show_form=show_form)


#para registrar un nuevo usuario y almacenarlo en la DB
@app.route("/register", methods=["GET", "POST"])
def register():
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
                return render_template("register.html")
                

                # Initialize DB session
            db_session = get_db_session()
            created_at = datetime.now(pytz.timezone("America/Mexico_City"))

            if not register_user(db_session, numero_control, apellido_paterno, apellido_materno, nombres, username, password, carrera, semestre, grupo):
                flash("Ese nombre de usuario ya está registrado. Por favor, elige otro.", "danger")
                return render_template("register.html")

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
            return render_template("register.html")

    return render_template("register.html")


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
                print("User found:", user)
                # Check if password matches (you should hash passwords in production)
                if user['password'] == password:
                    print("Password correct")
                    flask_session.permanent = True
                    flask_session['username'] = username
                    flask_session['last_activity'] = datetime.now().isoformat()
                    flash(f'{username} inició sesión correctamente', 'success')
                    return redirect(url_for('hello_pm1'))  # Redirect on success
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












@app.route('/logout')
def logout():
    
    session.pop('username', None)
    
    return redirect(url_for('login'))


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()