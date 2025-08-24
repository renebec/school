import os
from flask import Flask, render_template, jsonify, send_from_directory, current_app
from gevent import monkey; monkey.patch_all()
from gevent.pywsgi import WSGIServer
from database import load_pg_from_db, load_pgn_from_db
from werkzeug.utils import secure_filename

from database import load_pgn_from_db, insert_actividad

import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")


@app.route("/")
def hello_pm1():
  pg = load_pg_from_db()
  return render_template('home.html',
                        pg=pg)



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




@app.route("/actividad/<int:id>", methods=["GET", "POST"])
def show_actividad(id):
    actividad = load_pgn_from_db(id)

    if not actividad:
        return render_template("error.html", message="actividad no encontrada."), 404

    show_form = True  # decide if you want to show the form here
    i = actividad

    if request.method == "POST":
        try:
            # Obtener datos del formulario
            actividad_num = request.form['actividad_num']
            apellido_paterno = request.form['apellido_paterno']
            apellido_materno = request.form['apellido_materno']
            nombres = request.form['nombres']
            semestre = request.form['semestre']
            grupo = request.form['grupo']
            pdf_file = request.files['pdf_file']

            # Validar PDF
            if not pdf_file or not pdf_file.filename.endswith('.pdf'):
                flash("Debes subir un archivo PDF válido.", "danger")
                return redirect(request.url)

            # Subir a Cloudinary
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type='raw',
                folder='actividades_pdf'
            )
            pdf_url = result['secure_url']
            print("✅ Upload to Cloudinary successful")

            # Guardar en base de datos
            insert_actividad(
                actividad_num,
                apellido_paterno,
                apellido_materno,
                nombres,
                semestre,
                grupo,
                pdf_url
            )
            print("✅ Insert into DB successful")
            flash(f"Actividad {actividad_num} enviada correctamente.", "success")
            return redirect("/")
            #return redirect(url_for("show_actividad", id=id))

        except Exception as e:
            print("❌ Error during submission:", e)
            flash(f"Ocurrió un error al procesar la actividad {actividad_num}.", "danger")
            return redirect("/")

    return render_template("classpage.html", i=actividad, show_form=show_form)
  

if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()