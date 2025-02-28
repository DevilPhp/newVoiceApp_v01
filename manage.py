import os
import sys
import click
from flask.cli import FlaskGroup
from app import createApp
from app.extensions import db

app = createApp()
cli = FlaskGroup(app)


@cli.command("create_db")
def create_db():
    """Create all database tables."""
    db.create_all()
    click.echo("Database tables created!")


@cli.command("drop_db")
def drop_db():
    """Drop all database tables."""
    if click.confirm("Are you sure you want to drop all tables?"):
        db.drop_all()
        click.echo("Database tables dropped!")


# @cli.command("seed_db")
# def seed_db():
#     """Seed the database with initial data."""
#     from app.models.user import User
#
#     # Create a test user
#     test_user = User(
#         username="testuser",
#         email="test@example.com",
#         password_hash="pbkdf2:sha256:150000$notarealhash$"  # Not a real hash, just for demonstration
#     )
#
#     db.session.add(test_user)
#     db.session.commit()
#
#     click.echo("Database seeded with test data!")


if __name__ == "__main__":
    cli()