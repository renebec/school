
from werkzeug.utils import secure_filename
import os
from flask import Flask, render_template, jsonify, send_from_directory, current_app, request, redirect, url_for, flash, session
from gevent import monkey; monkey.patch_all()
from gevent.pywsgi import WSGIServer
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader


from database import load_pg_from_db, load_pgn_from_db,  register_user, get_db_session, insert_actividad

from sqlalchemy import text

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


cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

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

    if request.method == "POST":
        try:
            actividad_num = request.form['actividad_num']
            numero_control = request.form['numero_control']
            pdf_file = request.files['pdf_file']

            if not pdf_file or not pdf_file.filename.endswith('.pdf'):
                flash("Debes subir un archivo PDF válido.", "danger")
                return redirect(request.url)

            # Upload PDF to Cloudinary
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type='raw',
                folder='actividades_pdf'
            )
            print("Cloudinary upload result:", result)
            pdf_url = result['secure_url']

            # Get user info from DB using a session
            session = get_db_session()
            query = text("SELECT apellido_paterno, apellido_materno, nombres, carrera, semestre, grupo FROM users WHERE numero_control = :nc")
            result = session.execute(query, {"nc": numero_control})
            user = result.mappings().first()
            session.close()

            if not user:
                flash("Número de control no encontrado.", "danger")
                return redirect(request.url)



            # Insert actividad in DB
            db_session = get_db_session()
            insert_actividad(
                db_session,
                actividad_num,
                user['apellido_paterno'],
                user['apellido_materno'],
                user['nombres'],
                user['carrera'],
                user['semestre'],
                user['grupo'],
                pdf_url,
                result['created_at']
            )
            db_session.close()

            flash(f"Actividad {actividad_num} enviada correctamente.", "success")
            return redirect(url_for("hello_pm1"))

        except Exception as e:
            print("❌ Error durante el envío:", e)
            flash("Error al enviar la actividad.", "danger")
            return redirect(request.url)

    return render_template("enviaractividad.html")






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

            # Call the function to register the user (make sure it handles the db insertion)
            register_user(numero_control, apellido_paterno, apellido_materno, nombres, username, password, carrera, semestre, grupo)

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
        
        try:
            # Connect to the database and fetch user data by username
            conn = get_db_connection()
            query = text('SELECT * FROM users WHERE username = :username')
            result = conn.execute(query, {'username': username}).fetchone()
            conn.close()
            
            if result:
                # Check if password matches (you should use hashed passwords in production)
                if result.password == password:
                    session.permanent = True
                    session['username'] = username
                    session['last_activity'] = datetime.now().isoformat()
                    flash(f'{username} inició sesión', 'success')
                    return redirect(url_for('hello_pm1'))
                else:
                    redirect(url_for('login.html'))
                    #flash('Invalid password. Please try again.', 'danger')
            else:
                render_template('login.html')
                #flash('Username not found. Please try again.', 'danger')
                
        except Exception:
            render_template('login.html')
            #flash('', 'danger')

    return render_template('login.html')





@app.route('/logout')
def logout():
    session.pop('username', None)
    #flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()