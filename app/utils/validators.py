from app.models.soporteplus_models import Usuario


class Validators:

    # validar el cambio de rol
    @staticmethod
    def validate_user_role_change(user_id, data):
        # buscar el usuario
        current_user_role_valid = Usuario.query.get(user_id)
        # validar que el usuario exista
        if not current_user_role_valid:
            return None
        # validar que el usuario no pueda cambiar su propio rol
        if (
            "ID_Rol" in data
            and int(current_user_role_valid.ID_Rol) == user_id
            and current_user_role_valid.is_admin
            and data["ID_Rol"] != user_id
        ):
            return None
        return current_user_role_valid

    # valida que el correo exista
    @staticmethod
    def email_exists(email, user_id):
        return Usuario.query.filter(
            Usuario.email == email, Usuario.ID_usuario != user_id
        ).first()

    # actualización de password sobre la instancia de usuario
    @staticmethod
    def validate_password_update(user, data):
        if "password" in data and data["password"]:
            user.set_password(data["password"])

#validar que el correo exista
def email_exists(email, user_id):
    return Validators.email_exists(email, user_id)

#validar el cambio de rol
def validate_user_role_change(user_id, data):
    return Validators.validate_user_role_change(user_id, data)

#validar la actualizacion de password
def validate_password_update(user, data):
    return Validators.validate_password_update(user, data)
