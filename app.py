import os
from flask import Flask, render_template, jsonify, send_from_directory, current_app, request, redirect, url_for, flash, session
from gevent import monkey; monkey.patch_all()
from gevent.pywsgi import WSGIServer
#from database import load_pg_from_db, load_pgn_from_db, get_db_connection
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from database import load_pg_from_db, load_pgn_from_db, get_db_connection, insert_actividad, register_user

from sqlalchemy import text

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


@app.route("/")
def hello_pm1():
        if 'user' not in session:
            return redirect(url_for('login'))  # Redirige al login si no ha iniciado sesión

        pg = load_pg_from_db()
        return render_template('home.html', pg=pg)



@app.route('/pg/<int:pg_id>') 
def show_pg(pg_id):
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

        if not numero_control or not username or not password:
            return "Todos los campos son obligatorios", 400

        # Aquí guardas en la base de datos
        register_user(numero_control, username, password)

        return redirect(url_for('login'))

    return render_template('register.html')





@app.route('/login', methods=['GET', 'POST'])
def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            with get_db_connection() as conn:
                result = conn.execute(text('SELECT * FROM users WHERE username = :username'), {'username': username})
                user = result.mappings().first()

            print("User found:", user)  # Debug

            if user:
                print("Checking password...")
                if check_password_hash(user['password'], password):
                    flash('Login successful!', 'success')
                    return redirect(url_for('home'))
                else:
                    print("Password incorrect")
            else:
                print("User not found")

            flash('Invalid username or password. Please try again.', 'danger')

        return render_template('login.html')
  

if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()