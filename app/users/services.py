from app.models.soporteplus_models import Usuario
from app.utils.validators import email_exists, validate_user_role_change, validate_password_update
from app import db

class UserService:
    # validar si el usuario es administrador
    @staticmethod
    def is_admin(user_id):
        user = Usuario.query.get(int(user_id))
        #retornar True si el usuario es administrador, False en caso contrario
        return bool(user and user.is_admin)

    # obtener todos los usuarios
    @staticmethod
    def get_all_users():
        usuarios = Usuario.query.all()
        # retornar una lista de diccionarios con los datos de los usuarios
        return[{
            "id": usuario.ID_usuario,
            "email": usuario.email,
            "nombre": usuario.Nombre,
            "rol_id": usuario.ID_Rol,
            "is_admin": usuario.is_admin,
        } for usuario in usuarios]
        
       
    # obtener un usuario por id
    @staticmethod
    def get_user_by_id(get_user_id):
        #obtener el usuario por id
        id_user = Usuario.query.get(get_user_id)
        #validar que el usuario exista
        if not id_user:
            return None
        #retornar los datos del usuario
        return {
            "id": id_user.ID_usuario,
            "email": id_user.email,
            "nombre": id_user.Nombre,
            "rol_id": id_user.ID_Rol,
            "is_admin": id_user.is_admin,
        }

    #actualizar usuario
    @staticmethod
    def update_user(user_id, data):
        #buscar el usuario
        current_user = Usuario.query.get(user_id)

        #validar que el usuario exista
        if not current_user:
            return None

        #validar el email
        if "email" in data:
            email = data["email"].strip()
            if email_exists(email, user_id):
                return None

        #validar el cambio de rol
        validate_user_role_change(user_id, data)

        #verificar si el password esta en los datos
        validate_password_update(current_user, data)

        #definir el mapeo de campos
        FIELD_MAP = {
            # campo_api: (atributo_modelo, transformacion)
            "email": ("email", lambda v: v.strip().lower()),
            #campo nombre
            "nombre": ("Nombre", lambda v: v.strip()),
            #campo rol_id
            "rol_id": ("ID_Rol", lambda v: v),
            #campo is_admin
            "is_admin": ("is_admin", lambda v: v),
        }
        #actualizar los campos
        for field, (attr, transform) in FIELD_MAP.items():
            if field in data:
                setattr(current_user, attr, transform(data[field]))
        #guardar los cambios
        db.session.commit()
        #retornar el usuario actualizado
        return {
            "id": current_user.ID_usuario,
            "email": current_user.email,
            "nombre": current_user.Nombre,
            "rol_id": current_user.ID_Rol,
            "is_admin": current_user.is_admin,
        }