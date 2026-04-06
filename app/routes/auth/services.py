from app.models.soporteplus_models import Usuario


def register_user(nombre, email, password, id_rol=2):
    """
    Create and persist a new user.
    Raises ValueError if the email or username is already taken.
    """
    if Usuario.query.filter_by(email=email).first():
        raise ValueError("El email ya existe")
    if Usuario.query.filter_by(Nombre=nombre).first():
        raise ValueError("El nombre de usuario ya existe")
    user = Usuario(Nombre=nombre, email=email, ID_Rol=id_rol)
    user.set_password(password)
    user.save()
    return user


def authenticate_user(email, password):
    """
    Verify credentials and return the user.
    Raises ValueError on invalid credentials or inactive account.
    """
    user = Usuario.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise ValueError("Credenciales inválidas")
    if not user.is_active:
        raise ValueError("Cuenta desactivada")
    return user


def get_user_by_id(user_id):
    """Return the user or raise 404."""
    return Usuario.query.get_or_404(int(user_id))
