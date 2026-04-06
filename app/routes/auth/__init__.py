from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from . import services
from .schemas import LoginSchema, RegisterSchema

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    schema = RegisterSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    try:
        user = services.register_user(
            nombre=data["nombre"],
            email=data["email"],
            password=data["password"],
            id_rol=data["ID_Rol"],
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    tokens = user.get_tokens()
    return jsonify({
        "message": "Usuario registrado exitosamente",
        "user": {
            "id": user.ID_usuario,
            "nombre": user.Nombre,
            "email": user.email,
            "ID_Rol": user.ID_Rol,
        },
        "tokens": tokens,
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    schema = LoginSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    try:
        user = services.authenticate_user(data["email"], data["password"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    tokens = user.get_tokens()
    return jsonify({
        "message": "Inicio de sesión exitoso",
        "user": {
            "id": user.ID_usuario,
            "nombre": user.Nombre,
            "email": user.email,
            "ID_Rol": user.ID_Rol,
            "is_admin": user.is_admin,
        },
        "tokens": tokens,
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    user = services.get_user_by_id(user_id)
    return jsonify({
        "user": {
            "id": user.ID_usuario,
            "nombre": user.Nombre,
            "email": user.email,
            "ID_Rol": user.ID_Rol,
            "is_admin": user.is_admin,
        }
    })
