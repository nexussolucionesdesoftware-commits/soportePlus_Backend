#importar el blueprint de flask
from flask import Blueprint, jsonify
#importar el decorador jwt_required
from flask_jwt_extended import get_jwt_identity, jwt_required
#importar el modelo de usuario
from app.models.soporteplus_models import Usuario
#importar el servicio de usuarios
from app.users.services import UserService

#definir el blueprint de usuarios
users_bp = Blueprint("users", __name__)

#obtener todos los usuarios
@users_bp.route("/", methods=["GET"])
@jwt_required()
def get_users():
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
    #obtener el id del usuario actual
    current_user_id = get_jwt_identity()
    #validar que el id del usuario actual sea diferente al id del usuario a obtener
    if int(current_user_id) != user_id:
        #validar que el usuario actual sea administrador
        if not UserService.is_admin(current_user_id):
            #retornar un error si el usuario no es administrador
            return jsonify({"error": "No autorizado"}), 403
        #obtener el usuario por id
    user_404 = Usuario.query.get_or_404(user_id)
    #retornar los datos del usuario
    return jsonify({"user": user_404})
