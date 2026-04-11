"""Data access style 1: SQLAlchemy ORM query chaining."""


def get_active_users(session):
    """Query active users via ORM filter chain."""
    return session.query(User).filter(User.active == True).all()


def get_user_by_id(session, user_id):
    """Retrieve a single user record."""
    return session.query(User).filter_by(id=user_id).first()
