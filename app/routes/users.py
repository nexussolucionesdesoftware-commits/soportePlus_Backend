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
        return jsonify({"error": "User not found"}), 404

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

    # Users can only see their own profile or admin can see all
    if int(current_user_id) != user_id:
        current_user = Usuario.query.get(current_user_id)
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Access denied"}), 403

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
        return jsonify({"error": "Current user not found"}), 404

    # Users can only edit their own profile or admin can edit all
    if int(current_user_id) != user_id and not current_user.is_admin:
        return (
            jsonify({"error": "Access denied. You can only edit your own profile"}),
            403,
        )

    # Find the user to update
    user_to_update = Usuario.query.get(user_id)
    if not user_to_update:
        return jsonify({"error": "User not found"}), 404

    # Validate request data
    schema = UpdateUserSchema()
    try:
        data = schema.load(request.json or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # If no data provided, return error
    if not data:
        return jsonify({"error": "No data provided for update"}), 400

    # Check if email is being changed and if it's unique
    if "email" in data and data["email"] != user_to_update.email:
        existing_user = Usuario.query.filter_by(email=data["email"]).first()
        if existing_user:
            return jsonify({"error": "Email already exists"}), 400

    # Check if name is being changed and if it's unique
    if "nombre" in data and data["nombre"] != user_to_update.Nombre:
        existing_user = Usuario.query.filter_by(Nombre=data["nombre"].strip()).first()
        if existing_user:
            return jsonify({"error": "Username already exists"}), 400

    # Only admins can change roles
    if "ID_Rol" in data and not current_user.is_admin:
        return jsonify({"error": "Only admins can change user roles"}), 403

    # Prevent admin from demoting themselves
    if (
        "ID_Rol" in data
        and int(current_user_id) == user_id
        and current_user.is_admin
        and data["ID_Rol"] != 1
    ):
        return (
            jsonify({"error": "Cannot remove admin privileges from your own account"}),
            400,
        )

    try:
        # Update fields
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
                    "message": "User updated successfully",
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
        return jsonify({"error": "Failed to update user", "details": str(e)}), 500


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
        return jsonify({"error": "User not found"}), 404

    # Only admins can delete users
    if not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    # Users cannot delete themselves
    if int(current_user_id) == user_id:
        return jsonify({"error": "Cannot delete your own account"}), 400

    # Find the user to delete
    user_to_delete = Usuario.query.get(user_id)
    if not user_to_delete:
        return jsonify({"error": "User not found"}), 404

    # Check if user has active tickets assigned
    if (
        hasattr(user_to_delete, "tiquets_asignados")
        and user_to_delete.tiquets_asignados
    ):
        active_tickets = [
            t for t in user_to_delete.tiquets_asignados if t.ID_estado != 3
        ]  # Assuming 3 = closed
        if active_tickets:
            return (
                jsonify(
                    {
                        "error": "Cannot delete user with active assigned tickets",
                        "active_tickets_count": len(active_tickets),
                    }
                ),
                400,
            )

    try:
        # Store user info for response
        deleted_user_info = {
            "id": user_to_delete.ID_usuario,
            "nombre": user_to_delete.Nombre,
            "email": user_to_delete.email,
        }

        # Delete the user (related logs and comments will be handled by cascade or remain as historical data)
        db.session.delete(user_to_delete)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "User deleted successfully",
                    "deleted_user": deleted_user_info,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete user", "details": str(e)}), 500


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
