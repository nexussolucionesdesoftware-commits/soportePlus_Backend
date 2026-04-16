"""Lógica de negocio de usuarios (consultas y mutaciones en BD, sin Flask/JWT)."""
from sqlalchemy import select

from app.models.soporteplus_models import Usuario
from app.utils.validators import email_exists, validate_user_role_change, validate_password_update
from app import db

class UserService:
    """Operaciones sobre ``Usuario`` usando SQLAlchemy (``db.session``)."""
    # validar si el usuario es administrador
    @staticmethod
    def is_admin(user_id):
        """
        Indica si el usuario tiene rol de administrador (``ID_Rol == 1`` vía modelo).

        Args:
            user_id: Identificador del usuario (se convierte a ``int``).

        Returns:
            True si existe y es admin; False si no existe o no lo es.
        """
        #buscar el usuario por id
        user = db.session.get(Usuario, int(user_id))
        #retornar True si el usuario es administrador, False en caso contrario
        return bool(user and user.is_admin)

    # obtener todos los usuarios
    @staticmethod
    def get_all_users():
        """
        Devuelve todos los usuarios como lista de diccionarios serializables.

        Returns:
            Lista de dicts con ``id``, ``email``, ``nombre``, ``rol_id``, ``is_admin``.
        """
        usuarios_todos = db.session.execute(select(Usuario)).scalars().all()
        # retornar una lista de diccionarios con los datos de los usuarios
        return[{
            "id": usuarios.ID_usuario,
            "email": usuarios.email,
            "nombre": usuarios.Nombre,
            "rol_id": usuarios.ID_Rol,
            "is_admin": usuarios.is_admin,
        } for usuarios in usuarios_todos]
        
    
    # obtener un usuario por id
    @staticmethod
    def get_user_by_id(get_user_id):
        """
        Busca un usuario por clave primaria.

        Args:
            get_user_id: ID del usuario.

        Returns:
            Diccionario con datos básicos o ``None`` si no existe.
        """
        #obtener el usuario por id
        id_user = db.session.get(Usuario, get_user_id)
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
        """
        Aplica cambios parciales validados previamente en la capa HTTP.

        Puede devolver ``None`` si el usuario no existe, si el email ya está en uso
        por otro registro, o si los validadores lanzan excepción.

        Args:
            user_id: ID del usuario a modificar.
            data: Campos permitidos (email, nombre, rol_id, is_admin, etc.).

        Returns:
            Dict con el usuario actualizado o ``None`` ante conflicto / no encontrado.
        """
        #buscar el usuario
        current_user = db.session.get(Usuario, user_id)

        #validar que el usuario exista
        if not current_user:
            return None

        #validar el email
        if "email" in data:
            email = data["email"].strip()
            #validar que el email no exista
            if email_exists(email, user_id):
                #retornar None si el email ya existe
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

    @staticmethod
    def delete_user(user_id):
        """
        Elimina un usuario de la base de datos si no tiene tickets activos asignados.

        No comprueba JWT ni rol: la autorización debe aplicarse en la capa HTTP.

        Args:
            user_id: ID numérico del usuario a eliminar.

        Returns:
            None si el usuario no existe.
            dict con ``error`` y opcionalmente ``active_tickets_count`` si tiene
            tickets asignados cuyo estado no es 3 (cerrado).
            dict con ``message`` y ``delete_user`` (datos básicos del eliminado) si OK.
            dict con ``error`` (mensaje con prefijo ``Error al eliminar usuario``)
            si falla el commit o la operación en BD.
        """
        user_to_delete = db.session.get(Usuario, user_id)
        #validar que el usuario exista
        if not user_to_delete:
            return None
        #validar que el usuario no tenga tickets asignados
        if user_to_delete.tiquets_asignados:
            # Estado 3 = cerrado; el resto se considera ticket activo para el borrado
            active_tickets = [
                t for t in user_to_delete.tiquets_asignados if t.Estado != 3
            ]
            if active_tickets:
                return {
                    "error": "No se puede eliminar el usuario con tickets activos o asignados",
                    "active_tickets_count": len(active_tickets),
                }

        try:
            # Copia mínima para la respuesta antes de borrar la fila
            deleted_user_info = {
                "id": user_to_delete.ID_usuario,
                "nombre": user_to_delete.Nombre,
                "email": user_to_delete.email,
            }
            user_to_delete.activo = False
            db.session.commit()
            return {
                "message": "Usuario desactivado exitosamente",
                "delete_user": deleted_user_info,
            }
        except Exception as e:
            db.session.rollback()
            return {"error": f"Error al eliminar usuario: {str(e)}" }
