
from werkzeug.utils import secure_filename
import os
from flask import Flask, render_template, jsonify, send_from_directory, current_app, request, redirect, url_for, flash, session
from gevent import monkey; monkey.patch_all()
from gevent.pywsgi import WSGIServer
from datetime import datetime, timedelta


from database import load_pg_from_db, load_pgn_from_db, get_db_connection, insert_actividad, register_user, get_user_from_database

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

import cloudinary
import cloudinary.uploader

#cloudinary.config( 
#  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
#  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
#  api_secret = os.environ.get("CLOUDINARY_API_SECRET")
#)

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
        flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
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



@app.route('/download/<path:filename>')
def download_file(filename):
    filename = secure_filename(filename)
    static_folder = current_app.static_folder  # Usually 'static'
    return send_from_directory(static_folder, filename, as_attachment=True)




@app.route("/enviaractividad", methods=["GET", "POST"])
def enviaractividad():
    if not check_session_timeout():
        flash('Su sesión ha expirado. Por favor, inicie sesión nuevamente.', 'danger')
        return redirect(url_for('login'))
        
    show_form = True
    if request.method == "POST":
        try:
            # Obtener los datos del formulario
            actividad_num = request.form['actividad_num']
            apellido_paterno = request.form['apellido_paterno']
            apellido_materno = request.form['apellido_materno']
            nombres = request.form['nombres']
            carrera = request.form['carrera']
            semestre = request.form['semestre']
            grupo = request.form['grupo']
            pdf_file = request.files['pdf_file']

            # Validar que el archivo sea un PDF
            if not pdf_file or not pdf_file.filename.endswith('.pdf'):
                flash("Debes subir un archivo PDF válido.", "danger")
                return redirect(request.url)

            # Subir el archivo PDF a Cloudinary
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type='raw',
                folder='actividades_pdf'
            )
            pdf_url = result['secure_url']
            print("✅ Carga en Cloudinary exitosa")

            # Insertar los datos en la base de datos
            insert_actividad(
                actividad_num,
                apellido_paterno,
                apellido_materno,
                nombres,
                carrera,
                semestre,
                grupo,
                pdf_url
            )
            print("✅ Inserción en DB exitosa")

            flash(f"Actividad {actividad_num} de {nombres} enviada correctamente.", "success")
            return redirect(url_for("hello_pm1"))  # Regresar a la página de inicio

        except Exception as e:
            print("❌ Error during submission:", e)
            flash(f"Ocurrió un error al procesar la actividad {actividad_num}.", "danger")
            return redirect("/")

    return render_template("enviaractividad.html", show_form=show_form)





# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        numero_control = request.form.get('numero_control')
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if numero_control exists in alumnos_preregistrados table
        conn = get_db_connection()
        query = text('SELECT * FROM alumnos_preregistrados WHERE numero_control = :numero_control')
        result = conn.execute(query, {'numero_control': numero_control}).fetchone()

        if not result:
            return "Número de control no registrado en la base de datos de alumnos preregistrados", 400

        if not username or not password:
            return "Todos los campos son obligatorios", 400

        # Save the user in the 'users' table after checking numero_control exists
        register_user(numero_control, username, password)

        return redirect(url_for('login'))

    return render_template('register.html')




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
                    flash(f'{username} inició sesión!', 'success')
                    return redirect(url_for('hello_pm1'))
                else:
                    redirect(url_for('login.html'))
                    #flash('Invalid password. Please try again.', 'danger')
            else:
                render_template('login.html')
                #flash('Username not found. Please try again.', 'danger')
                
        except Exception as e:
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