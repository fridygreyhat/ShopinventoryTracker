import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from models import User
from extensions import db

@click.command("create-superuser")
@with_appcontext
def create_superuser():
    username = input("Username: ")
    email = input("Email: ")
    password = input("Password: ")

    hashed_pw = generate_password_hash(password)

    user = User(username=username, email=email, password=hashed_pw, is_admin=True)
    db.session.add(user)
    db.session.commit()

    print(f"Superuser '{username}' created.")

# Register the command with Flask CLI
def register_commands(app):
    app.cli.add_command(create_superuser)
