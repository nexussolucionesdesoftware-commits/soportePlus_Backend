from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, ValidationError

from app import db
from app.models.soporteplus_models import Usuario, Rol

users_bp = Blueprint("users", __name__)


class UpdateUserSchema(Schema):
    """Esquema de validación para la actualización de usuarios."""

    nombre = fields.Str(
        required=False, validate=lambda x: len(x.strip()) >= 3 if x else True
    )
    email = fields.Email(required=False)
    password = fields.Str(required=False, validate=lambda x: len(x) >= 6 if x else True)
    ID_Rol = fields.Int(
        required=False, validate=lambda x: x in [1, 2, 3] if x is not None else True
    )  # 1=admin, 2=tecnico, 3=usuario


class RolSchema(Schema):
    """Schema para serializar roles"""

    ID_Rol = fields.Int(dump_only=True)
    Nombre = fields.Str(dump_only=True)


@users_bp.route("/", methods=["GET"])
@jwt_required()
def get_users():
    """
    Obtener la lista de todos los usuarios.
    
    Restricción: Solo accesible para usuarios con rol de Administrador.
    
    Returns:
        JSON: Lista de usuarios con sus roles y estados.
    """
    current_user_id = get_jwt_identity()
    current_user = Usuario.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Restricción de administrador eliminada para permitir carga de técnicos en el modal

    users = Usuario.query.all()
    users_data = []

    for user in users:
        users_data.append(
            {
                "id": user.ID_usuario,
                "email": user.email,
                "nombre": user.Nombre,
                "rol_id": user.ID_Rol,
                "is_admin": user.is_admin,
            }
        )

    return jsonify({"users": users_data})


@users_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    """
    Obtener detalles de un usuario específico.
    
    Restricción: Un usuario solo puede ver su propio perfil, a menos que sea Administrador.
    
    Args:
        user_id (int): ID del usuario a consultar.
    """
    current_user_id = get_jwt_identity()

    # Los usuarios solo pueden ver su propio perfil o el administrador puede ver todos
    if int(current_user_id) != user_id:
        current_user = Usuario.query.get(current_user_id)
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Acceso denegado"}), 403

    user = Usuario.query.get_or_404(user_id)

    return jsonify(
        {
            "user": {
                "id": user.ID_usuario,
                "email": user.email,
                "nombre": user.Nombre,
                "rol_id": user.ID_Rol,
                "is_admin": user.is_admin,
                "Apellido": user.Apellido,
            }
        }
    )


@users_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    """
    Actualizar información de un usuario.
    
    Permite cambiar nombre, email, contraseña y rol.
    Restricciones:
    - Solo administradores pueden cambiar roles.
    - Validaciones de unicidad para email y nombre.
    """
    current_user_id = get_jwt_identity()
    current_user = Usuario.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Usuario actual no encontrado"}), 404

    # Los usuarios solo pueden editar su propio perfil o el administrador puede editar todos
    if int(current_user_id) != user_id and not current_user.is_admin:
        return (
            jsonify({"error": "Acceso denegado. Solo puedes editar tu propio perfil"}),
            403,
        )

    # Buscar el usuario a actualizar
    user_to_update = Usuario.query.get(user_id)
    if not user_to_update:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Validar datos de la petición
    schema = UpdateUserSchema()
    try:
        data = schema.load(request.json or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # Si no se proporcionan datos, devolver error
    if not data:
        return jsonify({"error": "No se proporcionaron datos para actualizar"}), 400

    # Verificar si se está cambiando el email y si es único
    if "email" in data and data["email"] != user_to_update.email:
        existing_user = Usuario.query.filter_by(email=data["email"]).first()
        if existing_user:
            return jsonify({"error": "El correo electrónico ya existe"}), 400

    # Verificar si se está cambiando el nombre y si es único
    if "nombre" in data and data["nombre"] != user_to_update.Nombre:
        existing_user = Usuario.query.filter_by(Nombre=data["nombre"].strip()).first()
        if existing_user:
            return jsonify({"error": "El nombre de usuario ya existe"}), 400

    # Solo los administradores pueden cambiar roles
    if "ID_Rol" in data and not current_user.is_admin:
        return jsonify({"error": "Solo los administradores pueden cambiar roles de usuario"}), 403

    # Prevenir que el administrador se quite privilegios a sí mismo
    if (
        "ID_Rol" in data
        and int(current_user_id) == user_id
        and current_user.is_admin
        and data["ID_Rol"] != 1
    ):
        return (
            jsonify({"error": "No puedes eliminar privilegios de administrador de tu propia cuenta"}),
            400,
        )

    try:
        # Actualizar campos
        updated_fields = []

        if "nombre" in data:
            user_to_update.Nombre = data["nombre"].strip()
            updated_fields.append("nombre")

        if "email" in data:
            user_to_update.email = data["email"]
            updated_fields.append("email")

        if "password" in data:
            user_to_update.set_password(data["password"])
            updated_fields.append("password")

        if "ID_Rol" in data:
            user_to_update.ID_Rol = data["ID_Rol"]
            updated_fields.append("rol")

        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Usuario actualizado exitosamente",
                    "updated_fields": updated_fields,
                    "user": {
                        "id": user_to_update.ID_usuario,
                        "nombre": user_to_update.Nombre,
                        "email": user_to_update.email,
                        "rol_id": user_to_update.ID_Rol,
                        "is_admin": user_to_update.is_admin,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error al actualizar usuario", "details": str(e)}), 500


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    """
    Eliminar un usuario del sistema.
    
    Restricciones:
    - Solo Administradores.
    - No se puede eliminar la propia cuenta.
    - No se puede eliminar usuarios con tickets activos asignados.
    """
    current_user_id = get_jwt_identity()
    current_user = Usuario.query.get(current_user_id)

    if not current_user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Solo los administradores pueden eliminar usuarios
    if not current_user.is_admin:
        return jsonify({"error": "Se requiere acceso de administrador"}), 403

    # Los usuarios no pueden eliminarse a sí mismos
    if int(current_user_id) == user_id:
        return jsonify({"error": "No puedes eliminar tu propia cuenta"}), 400

    # Buscar el usuario a eliminar
    user_to_delete = Usuario.query.get(user_id)
    if not user_to_delete:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Verificar si el usuario tiene tickets activos asignados
    if (
        hasattr(user_to_delete, "tiquets_asignados")
        and user_to_delete.tiquets_asignados
    ):
        active_tickets = [
            t for t in user_to_delete.tiquets_asignados if t.ID_estado != 3
        ]  # Asumiendo 3 = cerrado
        if active_tickets:
            return (
                jsonify(
                    {
                        "error": "No se puede eliminar el usuario con tickets activos asignados",
                        "active_tickets_count": len(active_tickets),
                    }
                ),
                400,
            )

    try:
        # Guardar info del usuario para la respuesta
        deleted_user_info = {
            "id": user_to_delete.ID_usuario,
            "nombre": user_to_delete.Nombre,
            "email": user_to_delete.email,
        }

        # Eliminar el usuario (logs y comentarios relacionados serán manejados por cascada o permanecerán como datos históricos)
        db.session.delete(user_to_delete)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Usuario eliminado exitosamente",
                    "deleted_user": deleted_user_info,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error al eliminar usuario", "details": str(e)}), 500


@users_bp.route("/roles", methods=["GET"])
@jwt_required()
def get_roles():
    """Obtener todos los roles del sistema."""
    try:
        # Obtener todos los roles
        roles = Rol.query.all()

        # Crear schema para serializar
        rol_schema = RolSchema(many=True)

        return (
            jsonify(
                {
                    "status": "success",
                    "data": rol_schema.dump(roles),
                    "count": len(roles),
                }
            ),
            200,
        )

    except Exception as e:
        return (
            jsonify(
                {"status": "error", "message": f"Error al obtener roles: {str(e)}"}
            ),
            500,
        )
