from werkzeug.security import generate_password_hash

password = "testpassword"
hashed_password = generate_password_hash(password)
print("Hashed password:", hashed_password)