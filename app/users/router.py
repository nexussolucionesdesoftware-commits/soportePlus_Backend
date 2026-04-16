"""Rutas HTTP del recurso usuarios (blueprint registrado con prefijo ``/api/users``)."""
#importar el blueprint de flask
from flask import Blueprint, jsonify, request
#importar el decorador jwt_required
from flask_jwt_extended import get_jwt_identity, jwt_required
#importar el modelo de usuario
from app import db
#importar el servicio de usuarios
from app.users.services import UserService
#importar el esquema de actualización de usuario
from app.users.schema import UpdateUserSchema
#importar el error de validación
from marshmallow import  ValidationError
#importar el request

#definir el blueprint de usuarios
users_bp = Blueprint("users", __name__)

#obtener todos los usuarios 
@users_bp.route("/", methods=["GET"])
@jwt_required()
def get_users():
    """
    Listar usuarios (requiere JWT; el usuario autenticado debe existir).

    decorador (ver comentario sobre la función).

    Returns:
        200: Lista bajo la clave ``users``.
        404: Usuario del token no encontrado.
        500: Error no controlado.
    """
    try:
        #obtener el id del usuario actual
        current_user_id = get_jwt_identity()
        #obtener el usuario actual
        current_user = UserService.get_user_by_id(current_user_id)
        #validar que el usuario exista
        if not current_user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        #obtener todos los usuarios
        users_data_json = UserService.get_all_users()
        #retornar los datos de los usuarios
        return jsonify({"users": users_data_json})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#obtener un usuario por id
@users_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    """
    Obtener un usuario por ID.

    Un usuario solo puede ver su propio perfil salvo que sea administrador.

    Returns:
        200: Usuario bajo la clave ``user`` (objeto ORM vía ``get_or_404``).
        403: Otro usuario sin permisos de administrador.
    """
    #obtener el id del usuario actual
    current_user_id = get_jwt_identity()
    #validar que el id del usuario actual sea diferente al id del usuario a obtener
    if int(current_user_id) != user_id:
        #validar que el usuario actual sea administrador
        if not UserService.is_admin(current_user_id):
            #retornar un error si el usuario no es administrador
            return jsonify({"error": "No autorizado"}), 403
    #obtener el usuario por id
    user = UserService.get_user_by_id(user_id)
    #validar que el usuario exista
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    #retornar los datos del usuario
    return jsonify({"user": user})

#actualizar un usuario
@users_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    """
    Actualizar datos de un usuario (validación con ``UpdateUserSchema``).

    Permisos: el propio usuario o un administrador.

    Returns:
        200: Usuario actualizado bajo ``user``.
        400: Cuerpo vacío, validación Marshmallow o reglas de negocio del servicio.
        403: Sin permiso para modificar a otro usuario.
        404: Usuario del token inexistente.
        500: Error no controlado en la actualización.
    """
    #obtener el id del usuario actual
    current_user_id = get_jwt_identity()
    #obtener el usuario actual
    current_user = UserService.get_user_by_id(current_user_id)
    #validar que el usuario exista
    if not current_user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    #validar permisos: solo admin o el mismo usuario
    if int(current_user_id) != user_id and not UserService.is_admin(current_user_id):
        return jsonify({"error": "No autorizado"}), 403
    #obtener los datos del usuario
    schema = UpdateUserSchema()
    try:
        # data a Json 
        data = schema.load(request.json or {})
        # validan que no puedan borrar su propoa ciuenta
    except ValidationError as err:
        # error 400 
        return jsonify({"errors": err.messages}), 400
    try:
        #validar que los datos del usuario sean validos
        if not data:
            return jsonify({"error": "No se proporcionaron datos para actualizar"}), 400
        #actualizar el usuario
        user_updated = UserService.update_user(user_id, data)
        if not user_updated:
            return jsonify({"error": "No se pudo actualizar el usuario"}), 400
        #retornar los datos del usuario actualizado
        return jsonify({"user": user_updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    """
    Eliminar un usuario (solo administradores).

    Endpoint: ``DELETE /api/users/<user_id>`` (según el prefijo del blueprint).

    Restricciones:
        - El solicitante debe existir y ser administrador.
        - No se puede eliminar la propia cuenta.
        - El servicio rechaza usuarios con tickets asignados no cerrados (estado != 3).

    Returns:
        200: Usuario eliminado (cuerpo con ``message`` y ``delete_user``).
        400: Regla de negocio (p. ej. auto-eliminación, tickets activos).
        403: Sin permisos de administrador.
        404: Usuario autenticado o usuario objetivo no encontrado.
        500: Error al persistir el borrado en BD.
    """
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(current_user_id)
    if not current_user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    if not UserService.is_admin(current_user_id):
        return jsonify({"error": "Se requiere acceso de administrador"}), 403
    if int(current_user_id) == user_id:
        return jsonify({"error": "No puedes desactivar tu propia cuenta"}), 400

    # Reglas de tickets / persistencia viven en el servicio
    result = UserService.delete_user(user_id)
    if result is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    if "error" in result:
        err = result["error"]
        # Mismo prefijo que arma ``UserService.delete_user`` en excepciones de BD
        status = 500 if err.startswith("Error al desactivar usuario") else 400
        return jsonify(result), status
    return jsonify(result), 200
