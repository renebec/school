from flask import Flask, render_template
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

@app.route("/")
def home():
    return render_template('home.html', username="Invitado", pg=[], es_profesor=False)

@app.route("/test")
def test():
    return "<h1>¡La aplicación Flask está funcionando!</h1>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)