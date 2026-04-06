"""
Módulo de gestión de usuarios para la API Soporte Plus.

Este módulo proporciona los endpoints necesarios para la gestión completa de usuarios,
incluyendo consulta, actualización, eliminación y gestión de roles.

Endpoints principales:
- GET /users: Obtener todos los usuarios (con restricciones de rol)
- GET /users/<id>: Obtener usuario específico
- PUT /users/<id>: Actualizar información de usuario
- DELETE /users/<id>: Eliminar usuario (solo admin)
- GET /users/roles: Obtener catálogo de roles

Endpoints de seguridad:
- Todos los endpoints requieren autenticación JWT
- Aplica restricciones basadas en roles (admin, técnico, usuario)
- Los usuarios solo pueden acceder/editar su propio perfil
- Los administradores tienen acceso completo

Todos los endpoints utilizan autenticación JWT y devuelven respuestas en formato JSON.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, ValidationError

from app import db
from app.models.soporteplus_models import Usuario, Rol

# Blueprint de Flask para las rutas de usuarios
users_bp = Blueprint("users", __name__)


# --- ESQUEMAS DE MARSHMALLOW ---


class UpdateUserSchema(Schema):
    """
    Esquema de validación para la actualización de usuarios.
    
    Campos validados:
    - nombre: String, mínimo 3 caracteres, opcional
    - email: Email válido, opcional
    - password: String, mínimo 6 caracteres, opcional
    - ID_Rol: Entero, valores válidos [1, 2, 3], opcional
      (1=admin, 2=tecnico, 3=usuario)
    """

    nombre = fields.Str(
        required=False, validate=lambda x: len(x.strip()) >= 3 if x else True
    )
    email = fields.Email(required=False)
    password = fields.Str(required=False, validate=lambda x: len(x) >= 6 if x else True)
    ID_Rol = fields.Int(
        required=False, validate=lambda x: x in [1, 2, 3] if x is not None else True
    )  # 1=admin, 2=tecnico, 3=usuario


class RolSchema(Schema):
    """
    Esquema para serializar roles del sistema.
    
    Campos:
    - ID_Rol: Identificador único del rol
    - Nombre: Nombre descriptivo del rol
    """

    ID_Rol = fields.Int(dump_only=True)
    Nombre = fields.Str(dump_only=True)


# ===============================================================================
# FIN DE LA LÓGICA DE MARSHMALLOW - AQUÍ TERMINAN LOS ESQUEMAS
# ===============================================================================
# A PARTIR DE AQUÍ COMIENZAN LOS ENDPOINTS DE LA API
# ===============================================================================


@users_bp.route("/", methods=["GET"])
@jwt_required()
def get_users():
    """
    Obtener la lista de todos los usuarios del sistema.

    Endpoint: GET /users/
    
    Restricción: Originalmente solo para administradores, pero ahora permite
    carga de técnicos para asignación en modales de tickets.

    Returns:
        200: JSON con lista de usuarios y sus datos básicos
        404: Usuario actual no encontrado
        500: Error interno del servidor
    """
    try:
        # =======================================================================
        # LÓGICA DE NEGOCIO (SERVICE LAYER) - MOVER A services.py
        # =======================================================================
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)

        if not current_user:
            # =======================================================================
            # CAPA DE PRESENTACIÓN (CONTROLLER) - QUEDARÍA EN routes.py
            # =======================================================================
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

        # =======================================================================
        # CAPA DE PRESENTACIÓN (CONTROLLER) - QUEDARÍA EN routes.py
        # =======================================================================
        return jsonify({"users": users_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================================================================
# SECCIÓN: ENDPOINTS DE CONSULTA DE USUARIOS
# ===============================================================================
# Estos endpoints manejan la obtención de información de usuarios


@users_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    """
    Obtener detalles de un usuario específico.

    Endpoint: GET /users/<user_id>
    
    Restricción: Un usuario solo puede ver su propio perfil, 
    a menos que sea Administrador (puede ver todos los perfiles).

    Args:
        user_id (int): ID del usuario a consultar.

    Returns:
        200: JSON con datos completos del usuario
        403: Acceso denegado (si no es admin ni el propio usuario)
        404: Usuario no encontrado
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


# ===============================================================================
# SECCIÓN: ENDPOINTS DE MODIFICACIÓN DE USUARIOS
# ===============================================================================
# Estos endpoints manejan la actualización y eliminación de usuarios


@users_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    """
    Actualizar información de un usuario existente.

    Endpoint: PUT /users/<user_id>
    
    Permite cambiar nombre, email, contraseña y rol.
    
    Restricciones:
    - Solo administradores pueden cambiar roles.
    - Usuarios solo pueden editar su propio perfil.
    - Validaciones de unicidad para email y nombre.
    - Los administradores no pueden eliminar sus propios privilegios.

    Request Body (JSON):
    {
        "nombre": string (opcional, min 3 chars),
        "email": email válido (opcional),
        "password": string (opcional, min 6 chars),
        "ID_Rol": int (opcional, solo admin, valores [1,2,3])
    }

    Returns:
        200: Usuario actualizado exitosamente
        400: Datos inválidos, email/nombre duplicado, o intento de eliminar privilegios propios
        403: Acceso denegado (si no es admin ni el propio usuario)
        404: Usuario no encontrado
        500: Error interno del servidor
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

    Endpoint: DELETE /users/<user_id>
    
    Restricciones:
    - Solo Administradores pueden eliminar usuarios.
    - No se puede eliminar la propia cuenta.
    - No se puede eliminar usuarios con tickets activos asignados.

    Args:
        user_id (int): ID del usuario a eliminar.

    Returns:
        200: Usuario eliminado exitosamente
        400: No se puede eliminar la propia cuenta o tiene tickets activos
        403: Se requiere acceso de administrador
        404: Usuario no encontrado
        500: Error interno del servidor
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


# ===============================================================================
# SECCIÓN: ENDPOINTS DE CATÁLOGOS
# ===============================================================================
# Estos endpoints manejan los catálogos del sistema (roles, permisos, etc.)


@users_bp.route("/roles", methods=["GET"])
@jwt_required()
def get_roles():
    """
    Obtener todos los roles disponibles en el sistema.

    Endpoint: GET /users/roles
    
    Proporciona el catálogo completo de roles para uso en formularios
    y asignación de permisos.

    Returns:
        200: JSON con lista de roles y sus datos
        500: Error interno del servidor
    """
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
