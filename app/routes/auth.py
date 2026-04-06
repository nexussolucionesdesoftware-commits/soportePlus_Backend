"""
Módulo de autenticación para la API Soporte Plus.

Este módulo proporciona los endpoints necesarios para la gestión de autenticación
de usuarios en el sistema, incluyendo registro, inicio de sesión y obtención
de información del usuario actual.

Endpoints:
- POST /auth/register: Registro de nuevos usuarios
- POST /auth/login: Inicio de sesión de usuarios existentes
- GET /auth/me: Obtener información del usuario autenticado

Todos los endpoints utilizan tokens JWT para la autenticación y devuelven
respuestas en formato JSON.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from marshmallow import Schema, fields, ValidationError

from app import db
from app.models.soporteplus_models import Usuario  # Usar el modelo Usuario real

# Blueprint de Flask para las rutas de autenticación
auth_bp = Blueprint('auth', __name__)


class RegisterSchema(Schema):
    """
    Esquema de validación para el registro de nuevos usuarios.
    
    Campos validados:
    - nombre: String, mínimo 3 caracteres, requerido
    - email: Email válido, requerido y único
    - password: String, mínimo 6 caracteres, requerido
    - ID_Rol: Entero, opcional, valores válidos [1, 2, 3], por defecto 2 (técnico)
    """
    nombre = fields.Str(required=True, validate=lambda x: len(x) >= 3)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 6)
    ID_Rol = fields.Int(required=False, load_default=2, validate=lambda x: x in [1, 2, 3] if x is not None else True)  # Por defecto rol técnico
#    Apellido = fields.Str(required=True, validate=lambda x: len(x) >= 3)

class LoginSchema(Schema):
    """
    Esquema de validación para el inicio de sesión de usuarios.
    
    Campos validados:
    - email: Email válido, requerido
    - password: String, requerido
    """
    email = fields.Email(required=True)
    password = fields.Str(required=True)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registrar un nuevo usuario en el sistema.
    
    Endpoint: POST /auth/register
    
    Proceso:
    1. Valida los datos de entrada usando RegisterSchema
    2. Verifica que el email no exista previamente
    3. Verifica que el nombre de usuario no exista previamente
    4. Crea el nuevo usuario con contraseña hasheada
    5. Genera tokens JWT de acceso y refresco
    6. Devuelve los datos del usuario creado y los tokens
    
    Request Body (JSON):
    {
        "nombre": "string (min 3 chars)",
        "email": "valid@email.com",
        "password": "string (min 6 chars)",
        "ID_Rol": "int (optional, 1-3, default: 2)"
    }
    
    Returns:
        201: Usuario registrado exitosamente
        400: Error de validación o email/nombre ya existe
        JSON con datos del usuario y tokens JWT
    """
    schema = RegisterSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    # Verificar si el usuario ya existe por email (más confiable que por nombre)
    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'El email ya existe'}), 400
    
    # Verificar si el nombre ya existe (verificación opcional)
    if Usuario.query.filter_by(Nombre=data['nombre']).first():
        return jsonify({'error': 'El nombre de usuario ya existe'}), 400
    
    # Crear nuevo usuario
    user = Usuario(
        Nombre=data['nombre'],
        email=data['email'],
        ID_Rol=data['ID_Rol']
    )
    user.set_password(data['password'])
    user.save()
    
    # Generar tokens
    tokens = user.get_tokens()
    
    return jsonify({
        'message': 'Usuario registrado exitosamente',
        'user': {
            'id': user.ID_usuario,
            'nombre': user.Nombre,
            'email': user.email,
            'ID_Rol': user.ID_Rol,
            #'Apellido': user.Apellido
        },
        'tokens': tokens
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Iniciar sesión de usuario existente.
    
    Endpoint: POST /auth/login
    
    Proceso:
    1. Valida las credenciales usando LoginSchema
    2. Busca el usuario por email
    3. Verifica la contraseña usando el método check_password
    4. Verifica que la cuenta esté activa
    5. Genera tokens JWT de acceso y refresco
    6. Devuelve los datos del usuario y los tokens
    
    Request Body (JSON):
    {
        "email": "valid@email.com",
        "password": "string"
    }
    
    Returns:
        200: Inicio de sesión exitoso con tokens y datos del usuario
        400: Error de validación de datos
        401: Credenciales inválidas o cuenta desactivada
        JSON con mensaje, datos del usuario y tokens JWT
    """
    schema = LoginSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    # Buscar usuario por email
    user = Usuario.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Credenciales inválidas'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Cuenta desactivada'}), 401
    
    # Generar tokens
    tokens = user.get_tokens()
    
    return jsonify({
        'message': 'Inicio de sesión exitoso',
        'user': {
            'id': user.ID_usuario,
            'nombre': user.Nombre,
            'email': user.email,
            'ID_Rol': user.ID_Rol,
            'is_admin': user.is_admin
        },
        'tokens': tokens
    })


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Obtener información del usuario actualmente autenticado.
    
    Endpoint: GET /auth/me
    
    Proceso:
    1. Extrae el ID del usuario del token JWT usando get_jwt_identity()
    2. Busca el usuario en la base de datos
    3. Devuelve los datos básicos del usuario
    
    Headers requeridos:
    Authorization: Bearer <token_jwt>
    
    Returns:
        200: Datos del usuario autenticado
        401: Token inválido o expirado
        404: Usuario no encontrado
        JSON con datos del usuario (id, nombre, email, rol, admin)
    """
    user_id = int(get_jwt_identity())  # Convertir de string a entero
    user = Usuario.query.get_or_404(user_id)
    
    return jsonify({
        'user': {
            'id': user.ID_usuario,
            'nombre': user.Nombre,
            'email': user.email,
            'ID_Rol': user.ID_Rol,
            'is_admin': user.is_admin
        }
    })