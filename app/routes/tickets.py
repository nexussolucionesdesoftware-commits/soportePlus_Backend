"""
Módulo de gestión de tickets para la API Soporte Plus.

Este módulo proporciona los endpoints necesarios para la gestión completa de tickets de soporte,
incluyendo creación, consulta, actualización, eliminación y gestión de comentarios y documentos.

Endpoints principales:
- GET /tickets: Obtener todos los tickets (con filtrado por rol)
- GET /tickets/<id>: Obtener ticket específico
- POST /tickets: Crear nuevo ticket
- PUT /tickets/<id>: Actualizar ticket existente
- DELETE /tickets/<id>: Eliminar ticket
- GET /tickets/<id>/comentarios: Obtener comentarios de ticket
- POST /tickets/<id>/comentarios: Agregar comentario a ticket

Endpoints de catálogos:
- GET /categorias: Obtener categorías de tickets
- GET /estados: Obtener estados posibles
- GET /ubicaciones: Obtener ubicaciones disponibles
- GET /criticidades: Obtener niveles de criticidad

Endpoints de estadísticas:
- GET /dashboard/stats: Obtener estadísticas del panel de control

Todos los endpoints utilizan autenticación JWT y devuelven respuestas en formato JSON.
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import Schema, ValidationError, fields, pre_load
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app import db
from app.models.soporteplus_models import (
    CatalogoCriticidad,
    CatTiquet,
    Comentarios,
    Documento,
    EstadoTiquet,
    Tiquet,
    Ubicaciones,
    Usuario,
)

# Blueprint de Flask para las rutas de tickets
bp = Blueprint("tickets", __name__)

# --- ESQUEMAS DE MARSHMALLOW ---


class DocumentoSchema(Schema):
    """
    Esquema para serializar documentos adjuntos a tickets.
    
    Campos serializados:
    - id: Identificador único del documento
    - nombre_original: Nombre original del archivo subido
    - ruta_relativa: Ruta donde se almacena el archivo
    - mimetype: Tipo MIME del archivo
    - tamano: Tamaño del archivo en bytes
    - fecha_creacion: Fecha de creación del registro
    - Id_Tiquet: ID del ticket al que pertenece
    """

    id = fields.Int(dump_only=True)
    nombre_original = fields.Str(dump_only=True)
    ruta_relativa = fields.Str(dump_only=True)
    mimetype = fields.Str(dump_only=True)
    tamano = fields.Int(dump_only=True)
    fecha_creacion = fields.DateTime(dump_only=True)
    Id_Tiquet = fields.Int(dump_only=True)  # Este sí existe


class TiquetSchema(Schema):
    """
    Esquema de Marshmallow para la serialización y validación de Tickets.

    Define los campos que se exponen en la API y cómo se procesan los datos de entrada,
    incluyendo la conversión de formatos de fecha y relaciones con otras entidades.

    Campos principales:
    - Id_Tiquet: Identificador único (solo lectura)
    - Categoria: ID de la categoría del ticket
    - Tel_ext: Teléfono/extensión (usado para guardar ID del creador)
    - Ubicacion: ID de la ubicación del ticket
    - Criticidad: ID del nivel de criticidad
    - Descripcion: Descripción detallada del problema
    - User_asig: ID del usuario asignado
    - Estado: ID del estado actual del ticket
    - Fecha_apertura: Fecha de apertura (convertida automáticamente)
    - fecha_apertura_input: Campo de entrada para fecha (formato dd-mm-yyyy)
    - Fecha_cierre: Fecha de cierre (solo lectura)

    Relaciones:
    - documentos: Lista de documentos adjuntos
    - categoria_rel: Datos de la categoría
    - ubicacion_rel: Datos de la ubicación
    - criticidad_rel: Datos de la criticidad
    - estado_rel: Datos del estado
    - usuario_asignado: Datos del usuario asignado
    """

    Id_Tiquet = fields.Int(dump_only=True)
    Categoria = fields.Int(allow_none=True)
    Tel_ext = fields.Str(allow_none=True)
    Ubicacion = fields.Int(allow_none=True)
    Criticidad = fields.Int(allow_none=True)
    Descripcion = fields.Str(allow_none=True)
    User_asig = fields.Int(allow_none=True)
    Estado = fields.Int(allow_none=True)
    Fecha_apertura = fields.Raw(allow_none=True)
    fecha_apertura_input = fields.Str(load_only=True, allow_none=True)
    Fecha_cierre = fields.Raw(allow_none=True, dump_only=True)

    # Relación con Documentos (Aparecerán automáticamente en los GET)
    documentos = fields.Nested("DocumentoSchema", many=True, dump_only=True)

    # Campos relacionados
    categoria_rel = fields.Nested("CatTiquetSchema", dump_only=True)
    ubicacion_rel = fields.Nested("UbicacionesSchema", dump_only=True)
    criticidad_rel = fields.Nested("CatalogoCriticidadSchema", dump_only=True)
    estado_rel = fields.Nested("EstadoTiquetSchema", dump_only=True)
    usuario_asignado = fields.Nested("UsuarioSchema", dump_only=True)

    @pre_load
    def convert_date_format(self, data, **kwargs):
        """
        Pre-procesamiento de datos antes de la validación.

        Convierte la fecha de entrada (dd-mm-yyyy) al formato compatible con la base de datos (date object).
        Si no se proporciona fecha, asigna la fecha actual.

        Args:
            data (dict): Datos crudos recibidos en la petición.
        
        Returns:
            dict: Datos procesados con la fecha convertida.
        
        Raises:
            ValidationError: Si el formato de fecha es inválido.
        """
        if "fecha_apertura_input" in data and data["fecha_apertura_input"]:
            try:
                fecha_input = data["fecha_apertura_input"]
                fecha_obj = datetime.strptime(fecha_input, "%d-%m-%Y").date()
                data["Fecha_apertura"] = fecha_obj
                del data["fecha_apertura_input"]
            except ValueError:
                raise ValidationError(
                    "Formato dd-mm-yyyy requerido", "fecha_apertura_input"
                )
        elif "Fecha_apertura" not in data or data.get("Fecha_apertura") is None:
            data["Fecha_apertura"] = datetime.utcnow().date()
        return data


class CatTiquetSchema(Schema):
    """
    Esquema para serializar categorías de tickets.
    
    Campos:
    - Categoria: ID de la categoría
    - Unidad_corresponde: Unidad o departamento correspondiente
    - Nombre: Nombre descriptivo de la categoría
    """
    Categoria = fields.Int(dump_only=True)
    Unidad_corresponde = fields.Str(allow_none=True)
    Nombre = fields.Str(allow_none=True)


class EstadoTiquetSchema(Schema):
    """
    Esquema para serializar estados de tickets.
    
    Campos:
    - ID_estado: Identificador único del estado
    - Nombre: Nombre del estado (ej: Abierto, En Progreso, Cerrado)
    - Descripcion: Descripción detallada del estado
    """
    ID_estado = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    Descripcion = fields.Str(allow_none=True)


class CatalogoCriticidadSchema(Schema):
    """
    Esquema para serializar niveles de criticidad.
    
    Campos:
    - ID_criti: Identificador único del nivel de criticidad
    - Nombre: Nombre descriptivo (ej: Baja, Media, Alta, Crítica)
    """
    ID_criti = fields.Int(dump_only=True)
    Nombre = fields.Str(allow_none=True)


class UbicacionesSchema(Schema):
    """
    Esquema para serializar ubicaciones.
    
    Campos:
    - Id_ubicacion: Identificador único de la ubicación
    - Nombre: Nombre de la ubicación (requerido)
    - Zona: Zona o área geográfica (opcional)
    """
    Id_ubicacion = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    Zona = fields.Str(allow_none=True)


class UsuarioSchema(Schema):
    """
    Esquema simplificado para serializar datos básicos de usuarios.
    
    Campos:
    - ID_usuario: Identificador único del usuario
    - Nombre: Nombre completo del usuario
    - ID_Rol: ID del rol del usuario
    """
    ID_usuario = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    ID_Rol = fields.Int(allow_none=True)


class ComentarioSchema(Schema):
    """
    Esquema para serializar comentarios de tickets.
    
    Campos:
    - ID_comentario: Identificador único del comentario
    - mensaje: Contenido del comentario
    - Tipo: Tipo de comentario ('Usuario' o 'tecnico')
    - Satisfaccion: Nivel de satisfacción (opcional)
    - usuario: ID del usuario que creó el comentario
    - Id_Tiquet: ID del ticket asociado
    - Fecha: Fecha de creación del comentario
    - usuario_rel: Datos del usuario (relación anidada)
    """

    ID_comentario = fields.Int(dump_only=True)
    mensaje = fields.Str(allow_none=True)
    Tipo = fields.Str(allow_none=True)
    Satisfaccion = fields.Int(allow_none=True)
    usuario = fields.Int(allow_none=True)
    Id_Tiquet = fields.Int(allow_none=True)
    Fecha = fields.Raw(allow_none=True)

    # Extra útil para UI
    usuario_rel = fields.Nested("UsuarioSchema", dump_only=True)


# Instanciar esquemas para uso en los endpoints
tiquet_schema = TiquetSchema()
tiquets_schema = TiquetSchema(many=True)
cat_tiquet_schema = CatTiquetSchema()
cat_tiquets_schema = CatTiquetSchema(many=True)
estados_schema = EstadoTiquetSchema(many=True)
criticidades_schema = CatalogoCriticidadSchema(many=True)
ubicaciones_schema = UbicacionesSchema(many=True)

comentario_schema = ComentarioSchema()
comentarios_schema = ComentarioSchema(many=True)

# ===============================================================================
# FIN DE LA LÓGICA DE MARSHMALLOW - AQUÍ TERMINAN LOS ESQUEMAS
# ===============================================================================
# A PARTIR DE AQUÍ COMIENZAN LOS ENDPOINTS DE LA API
# ===============================================================================


@bp.route("/tickets", methods=["GET"])
@jwt_required()
def get_tickets():
    """
    Obtener todos los tickets registrados en el sistema.

    Endpoint: GET /tickets
    
    Utiliza 'joinedload' para realizar una carga ansiosa (eager loading) de las relaciones
    (categoría, ubicación, criticidad, usuario, estado) y evitar el problema de N+1 consultas.

    Filtrado por rol:
    - Admin (Rol 1) y Técnicos (Rol 2): Ven todos los tickets
    - Usuarios (Rol 3): Ven solo tickets asignados a ellos o creados por ellos

    Returns:
        200: JSON con lista de tickets serializados y total de registros
        500: Error interno del servidor
    """
    try:
        # =======================================================================
        # LÓGICA DE NEGOCIO (SERVICE LAYER) - MOVER A services.py
        # =======================================================================
        current_user_id = int(get_jwt_identity())
        current_user = Usuario.query.get(current_user_id)

        # Query base con relaciones
        query = Tiquet.query.options(
            joinedload(Tiquet.categoria_rel),
            joinedload(Tiquet.ubicacion_rel),
            joinedload(Tiquet.criticidad_rel),
            joinedload(Tiquet.usuario_asignado),
            joinedload(Tiquet.estado_rel),
        )

        # Lógica de filtrado por roles
        if current_user:
            # Solo Usuarios (Rol 3) se filtran. Técnicos (Rol 2) y Admins (Rol 1) ven todo.
            if current_user.ID_Rol == 3:
                # Usuarios (Rol 3): Ven tickets asignados a ellos O creados por ellos
                # Usamos Tel_ext para guardar el ID del creador (workaround)
                query = query.filter(
                    or_(
                        Tiquet.User_asig == current_user_id,
                        Tiquet.Tel_ext == str(current_user_id),
                    )
                )

        tickets = query.all()

        # =======================================================================
        # CAPA DE PRESENTACIÓN (CONTROLLER) - QUEDARÍA EN routes.py
        # =======================================================================
        return jsonify(
            {
                "status": "success",
                "data": tiquets_schema.dump(tickets),
                "total": len(tickets),
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@jwt_required()
def get_ticket(ticket_id):
    """
    Obtener los detalles de un ticket específico por su ID.

    Endpoint: GET /tickets/<ticket_id>

    Args:
        ticket_id (int): ID del ticket a consultar.

    Returns:
        200: JSON con datos completos del ticket incluyendo relaciones y documentos
        404: Ticket no encontrado
        500: Error interno del servidor
    """
    try:
        ticket = (
            Tiquet.query.options(
                joinedload(Tiquet.categoria_rel),
                joinedload(Tiquet.ubicacion_rel),
                joinedload(Tiquet.criticidad_rel),
                joinedload(Tiquet.usuario_asignado),
                joinedload(Tiquet.estado_rel),
                joinedload(Tiquet.documentos),
            )
            .filter_by(Id_Tiquet=ticket_id)
            .first_or_404()
        )
        return jsonify({"status": "success", "data": tiquet_schema.dump(ticket)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================================================================
# SECCIÓN: ENDPOINTS DE COMENTARIOS DE TICKETS
# ===============================================================================
# Estos endpoints manejan la gestión de comentarios asociados a tickets


@bp.route("/tickets/<int:ticket_id>/comentarios", methods=["GET"])
@jwt_required()
def get_ticket_comentarios(ticket_id):
    """
    Obtener todos los comentarios de un ticket específico.
    
    Endpoint: GET /tickets/<ticket_id>/comentarios
    
    Args:
        ticket_id (int): ID del ticket a consultar.
    
    Returns:
        200: JSON con lista de comentarios ordenados por fecha
        404: Ticket no encontrado
        500: Error interno del servidor
    """
    try:
        # Verificar que el ticket existe
        ticket = Tiquet.query.filter_by(Id_Tiquet=ticket_id).first()
        if not ticket:
            return jsonify({"status": "error", "message": "Ticket no encontrado"}), 404

        comentarios = (
            Comentarios.query.options(joinedload(Comentarios.usuario_rel))
            .filter_by(Id_Tiquet=ticket_id)
            .order_by(Comentarios.ID_comentario.asc())
            .all()
        )

        return jsonify(
            {
                "status": "success",
                "data": comentarios_schema.dump(comentarios),
                "total": len(comentarios),
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/tickets/<int:ticket_id>/comentarios", methods=["POST"])
@jwt_required()
def add_ticket_comentario(ticket_id):
    """
    Agregar un nuevo comentario (seguimiento) a un ticket existente.
    
    Endpoint: POST /tickets/<ticket_id>/comentarios
    
    Args:
        ticket_id (int): ID del ticket al que se agregará el comentario.
    
    Request Body (JSON):
    {
        "mensaje": "Contenido del comentario",
        "comentario": "Contenido del comentario" (alternativo)
    }
    
    Returns:
        201: Comentario creado exitosamente
        400: Mensaje requerido o ticket no encontrado
        404: Ticket no encontrado
        500: Error interno del servidor
    """
    try:
        data = request.get_json() or {}
        mensaje = (data.get("mensaje") or data.get("comentario") or "").strip()

        if not mensaje:
            return jsonify(
                {"status": "error", "message": "El mensaje es requerido"}
            ), 400

        ticket = Tiquet.query.filter_by(Id_Tiquet=ticket_id).first()
        if not ticket:
            return jsonify({"status": "error", "message": "Ticket no encontrado"}), 404

        user_id = int(get_jwt_identity())
        user = Usuario.query.get(user_id)

        # Determinar tipo de comentario según rol del usuario
        # Enum en BD: ('Usuario', 'tecnico')
        tipo = (
            "tecnico"
            if (user and user.ID_Rol == 2) or (user and user.is_admin)
            else "Usuario"
        )

        comentario = Comentarios(
            mensaje=mensaje,
            Tipo=tipo,
            usuario=user_id,
            Id_Tiquet=ticket_id,
            Fecha=datetime.utcnow().date(),
        )

        db.session.add(comentario)
        db.session.commit()

        # Obtener comentario con relaciones para respuesta
        comentario_db = Comentarios.query.options(
            joinedload(Comentarios.usuario_rel)
        ).get(comentario.ID_comentario)

        return jsonify(
            {
                "status": "success",
                "message": "Comentario agregado",
                "data": comentario_schema.dump(comentario_db),
            }
        ), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================================================================
# SECCIÓN: ENDPOINTS CRUD PRINCIPALES DE TICKETS
# ===============================================================================
# Estos endpoints manejan las operaciones básicas de tickets (GET, POST, PUT, DELETE)


@bp.route("/tickets", methods=["POST"])
@jwt_required()
def create_ticket():
    """
    Crear un nuevo ticket en el sistema.

    Endpoint: POST /tickets

    Valida los datos de entrada utilizando TiquetSchema y asigna automáticamente
    el usuario actual como creador del ticket.

    Request Body (JSON):
    {
        "Categoria": int,
        "Tel_ext": string (opcional),
        "Ubicacion": int,
        "Criticidad": int,
        "Descripcion": string,
        "User_asig": int (opcional, se asigna automáticamente si no se especifica),
        "fecha_apertura_input": "dd-mm-yyyy" (opcional, usa fecha actual si no se especifica)
    }

    Returns:
        201: Ticket creado exitosamente con datos completos
        400: Datos inválidos o no proporcionados
        500: Error interno del servidor
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {"status": "error", "message": "No se proporcionaron datos"}
            ), 400

        # Forzar la asignación del ticket al usuario que lo crea si es un cliente (Rol 3)
        current_user_id = int(get_jwt_identity())
        current_user = Usuario.query.get(current_user_id)

        # Si no especifican un técnico (User_asig), se le asigna al usuario actual por defecto.
        if "User_asig" not in data or not data.get("User_asig"):
            data["User_asig"] = current_user_id

        # Guardar el ID del creador en el campo Tel_ext (que no se usa) para poder filtrar después
        # Esto permite que el usuario siga viendo el ticket aunque se lo asigne a un técnico
        data["Tel_ext"] = str(current_user_id)

        # Validar y transformar datos usando el schema
        try:
            validated_data = tiquet_schema.load(data)
        except ValidationError as err:
            # =======================================================================
            # CAPA DE PRESENTACIÓN (CONTROLLER) - QUEDARÍA EN routes.py
            # =======================================================================
            return jsonify(
                {
                    "status": "error",
                    "message": "Datos inválidos",
                    "errors": err.messages,
                }
            ), 400

        # =======================================================================
        # LÓGICA DE NEGOCIO (SERVICE LAYER) - MOVER A services.py
        # =======================================================================
        # Crear ticket con datos validados
        ticket = Tiquet(**validated_data)
        db.session.add(ticket)
        db.session.commit()
        
        # =======================================================================
        # CAPA DE PRESENTACIÓN (CONTROLLER) - QUEDARÍA EN routes.py
        # =======================================================================
        return jsonify(
            {
                "status": "success",
                "message": "Creado",
                "data": tiquet_schema.dump(ticket),
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/tickets/<int:ticket_id>", methods=["PUT"])
@jwt_required()
def update_ticket(ticket_id):
    """
    Actualizar la información de un ticket existente.

    Endpoint: PUT /tickets/<ticket_id>

    Args:
        ticket_id (int): ID del ticket a actualizar.

    Request Body (JSON):
    {
        "Categoria": int (opcional),
        "Ubicacion": int (opcional),
        "Criticidad": int (opcional),
        "Descripcion": string (opcional),
        "User_asig": int (opcional),
        "Estado": int (opcional)
    }

    Returns:
        200: Ticket actualizado exitosamente
        400: Datos inválidos
        404: Ticket no encontrado
        500: Error interno del servidor
    """
    try:
        # 1. Buscar el ticket existente
        ticket = Tiquet.query.get_or_404(ticket_id)

        # 2. Obtener los datos que envía el cliente
        data = request.get_json()

        # Validar datos (parcialmente, permite actualizar solo algunos campos)
        errors = tiquet_schema.validate(data, partial=True)
        if errors:
            return jsonify(
                {"status": "error", "message": "Datos inválidos", "errors": errors}
            ), 400

        # Obtener usuario actual para verificar permisos
        current_user_id = int(get_jwt_identity())
        current_user = Usuario.query.get(current_user_id)

        # Nota: Se permite que cualquier usuario autenticado edite tickets
        # para facilitar el seguimiento y actualización de información

        # Actualizar campos dinámicamente
        for key, value in data.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Ticket actualizado correctamente",
                "data": tiquet_schema.dump(ticket),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"status": "error", "message": f"Error al actualizar el ticket: {str(e)}"}
        ), 500


@bp.route("/tickets/<int:ticket_id>", methods=["DELETE"])
@jwt_required()
def delete_ticket(ticket_id):
    """
    Eliminar un ticket del sistema.

    Endpoint: DELETE /tickets/<ticket_id>

    Args:
        ticket_id (int): ID del ticket a eliminar.

    Returns:
        200: Ticket eliminado exitosamente
        404: Ticket no encontrado
        500: Error interno del servidor
    """
    try:
        ticket = Tiquet.query.get_or_404(ticket_id)

        # Eliminar registros relacionados primero si es necesario
        # SQLAlchemy manejará las cascadas según las configuraciones del modelo

        db.session.delete(ticket)
        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": f"Ticket {ticket_id} eliminado exitosamente",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/tickets/<int:ticket_id>/upload", methods=["POST"])
@jwt_required()
def close_ticket(ticket_id):
    """
    Cerrar un ticket formalmente.

    Endpoint: POST /tickets/<int:ticket_id>/upload

    Esta acción busca el estado 'Cerrado' en la base de datos, actualiza el estado del ticket
    y establece la fecha de cierre actual automáticamente.

    Args:
        ticket_id (int): ID del ticket a cerrar.

    Returns:
        200: Ticket cerrado exitosamente
        400: No se encontró estado "Cerrado" o el ticket ya está cerrado
        404: Ticket no encontrado
        500: Error interno del servidor
    """
    try:
        # 1. Buscar el ticket
        ticket = Tiquet.query.get_or_404(ticket_id)

        # Buscar el estado "cerrado"
        estado_cerrado = EstadoTiquet.query.filter_by(Nombre="Cerrado").first()
        if not estado_cerrado:
            # Si no encuentra "Cerrado", buscar por variaciones comunes
            estado_cerrado = EstadoTiquet.query.filter(
                EstadoTiquet.Nombre.ilike("%cerrado%")
                | EstadoTiquet.Nombre.ilike("%closed%")
                | EstadoTiquet.Nombre.ilike("%finalizado%")
            ).first()

        if not estado_cerrado:
            return jsonify(
                {
                    "status": "error",
                    "message": 'No se encontró un estado de "Cerrado" en el sistema',
                }
            ), 400

        # Verificar si el ticket ya está cerrado
        if ticket.Estado == estado_cerrado.ID_estado and ticket.Fecha_cierre:
            return jsonify(
                {
                    "status": "warning",
                    "message": "El ticket ya está cerrado",
                    "data": {
                        "Id_Tiquet": ticket.Id_Tiquet,
                        "Estado": ticket.Estado,
                        "Fecha_cierre": ticket.Fecha_cierre.strftime("%d-%m-%Y")
                        if ticket.Fecha_cierre
                        else None,
                    },
                }
            )

        # Cerrar el ticket
        ticket.Estado = estado_cerrado.ID_estado
        ticket.Fecha_cierre = datetime.utcnow().date()

        db.session.commit()
        return jsonify(
            {"status": "success", "data": tiquet_schema.dump(ticket)}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ENDPOINTS DE CATÁLOGOS ---

@bp.route("/categorias", methods=["GET"])
@jwt_required()
def get_categorias():
    """
    Obtener el catálogo completo de categorías de tickets.
    
    Endpoint: GET /categorias
    
    Returns:
        200: JSON con lista de todas las categorías disponibles
        500: Error interno del servidor
    """
    categorias = CatTiquet.query.all()
    return jsonify({"status": "success", "data": cat_tiquets_schema.dump(categorias)})


# --- ENDPOINTS DE ESTADÍSTICAS ---

@bp.route("/dashboard/stats", methods=["GET"])
@jwt_required()
def get_dashboard_stats():
    """
    Obtener estadísticas generales para el panel de control (Dashboard).

    Endpoint: GET /dashboard/stats

    Calcula totales de tickets, desglose por estado y por criticidad
    para generar gráficas y reportes. Aplica filtros de seguridad según el rol del usuario.

    Returns:
        200: JSON con estadísticas completas del dashboard
        500: Error interno del servidor
    """
    try:
        current_user_id = int(get_jwt_identity())
        current_user = Usuario.query.get(current_user_id)

        # Base query para conteos simples
        query = Tiquet.query

        # Aplicar filtros de seguridad (mismo que en get_tickets)
        if current_user:
            # Solo Usuarios (Rol 3) se filtran.
            if current_user.ID_Rol == 3:
                # Usuarios: Sus tickets (asignados o creados)
                query = query.filter(
                    or_(
                        Tiquet.User_asig == current_user_id,
                        Tiquet.Tel_ext == str(current_user_id),
                    )
                )

        total_tickets = query.count()

        # Tickets abiertos (reutilizando el query filtrado)
        tickets_abiertos = (
            query.join(EstadoTiquet).filter(EstadoTiquet.Nombre != "Cerrado").count()
        )

        tickets_cerrados = total_tickets - tickets_abiertos

        # Tickets por estado
        q_estado = db.session.query(
            EstadoTiquet.Nombre, db.func.count(Tiquet.Id_Tiquet)
        ).outerjoin(Tiquet)

        # Aplicar filtros a la query de estados
        if current_user:
            if current_user.ID_Rol == 3:
                q_estado = q_estado.filter(
                    or_(
                        Tiquet.User_asig == current_user_id,
                        Tiquet.Tel_ext == str(current_user_id),
                    )
                )

        tickets_por_estado = q_estado.group_by(EstadoTiquet.ID_estado).all()

        # Tickets por criticidad
        q_crit = db.session.query(
            CatalogoCriticidad.Nombre, db.func.count(Tiquet.Id_Tiquet)
        ).outerjoin(Tiquet)

        # Aplicar filtros a la query de criticidad
        if current_user:
            if current_user.ID_Rol == 3:
                q_crit = q_crit.filter(
                    or_(
                        Tiquet.User_asig == current_user_id,
                        Tiquet.Tel_ext == str(current_user_id),
                    )
                )

        tickets_por_criticidad = q_crit.group_by(CatalogoCriticidad.ID_criti).all()

        return jsonify(
            {
                "status": "success",
                "data": {
                    "total_tickets": total_tickets,
                    "tickets_abiertos": tickets_abiertos,
                    "tickets_cerrados": tickets_cerrados,
                    "tickets_por_estado": [
                        {"estado": estado, "cantidad": cantidad}
                        for estado, cantidad in tickets_por_estado
                    ],
                    "tickets_por_criticidad": [
                        {"criticidad": criticidad, "cantidad": cantidad}
                        for criticidad, cantidad in tickets_por_criticidad
                    ],
                },
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/categorias/<int:categoria_id>", methods=["PUT"])
@jwt_required()
def update_categoria(categoria_id):
    """
    Actualizar los datos de una categoría existente.

    Endpoint: PUT /categorias/<categoria_id>

    Args:
        categoria_id (int): ID de la categoría a actualizar.

    Request Body (JSON):
    {
        "Unidad_corresponde": string (opcional),
        "Nombre": string (opcional)
    }

    Returns:
        200: Categoría actualizada exitosamente
        400: Datos inválidos
        404: Categoría no encontrada
        500: Error interno del servidor
    """
    try:
        # Buscar la categoría
        categoria = CatTiquet.query.get(categoria_id)
        if not categoria:
            return jsonify(
                {"status": "error", "message": "Categoría no encontrada"}
            ), 404

        # Validar datos de entrada
        categoria_data = cat_tiquet_schema.load(request.json, partial=True)

        # Actualizar campos
        if "Unidad_corresponde" in categoria_data:
            categoria.Unidad_corresponde = categoria_data["Unidad_corresponde"]
        if "Nombre" in categoria_data:
            categoria.Nombre = categoria_data["Nombre"]

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Categoría actualizada exitosamente",
                "data": cat_tiquet_schema.dump(categoria),
            }
        )

    except ValidationError as e:
        return jsonify(
            {"status": "error", "message": "Datos inválidos", "errors": e.messages}
        ), 400
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"status": "error", "message": f"Error al actualizar categoría: {str(e)}"}
        ), 500


@bp.route("/categorias/<int:categoria_id>", methods=["DELETE"])
@jwt_required()
def delete_categoria(categoria_id):
    """
    Eliminar una categoría (si no está en uso).

    Endpoint: DELETE /categorias/<categoria_id>

    Args:
        categoria_id (int): ID de la categoría a eliminar.

    Returns:
        200: Categoría eliminada exitosamente
        400: La categoría está siendo utilizada por tickets
        404: Categoría no encontrada
        500: Error interno del servidor
    """
    try:
        # Buscar la categoría
        categoria = CatTiquet.query.get(categoria_id)
        if not categoria:
            return jsonify(
                {"status": "error", "message": "Categoría no encontrada"}
            ), 404

        # Verificar si la categoría está siendo usada por algún ticket
        tickets_usando_categoria = Tiquet.query.filter_by(
            Categoria=categoria_id
        ).first()
        if tickets_usando_categoria:
            return jsonify(
                {
                    "status": "error",
                    "message": "No se puede eliminar la categoría porque está siendo utilizada por uno o más tickets",
                }
            ), 400

        db.session.delete(categoria)
        db.session.commit()

        return jsonify(
            {"status": "success", "message": "Categoría eliminada exitosamente"}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"status": "error", "message": f"Error al eliminar categoría: {str(e)}"}
        ), 500


@bp.route("/estados", methods=["GET"])
@jwt_required()
def get_estados():
    """
    Obtener el catálogo de estados posibles para un ticket.
    
    Endpoint: GET /estados
    
    Returns:
        200: JSON con lista de todos los estados disponibles
        500: Error interno del servidor
    """
    estados = EstadoTiquet.query.all()
    return jsonify({"status": "success", "data": estados_schema.dump(estados)})


@bp.route("/ubicaciones", methods=["GET"])
@jwt_required()
def get_ubicaciones():
    """
    Obtener el catálogo de ubicaciones disponibles.
    
    Endpoint: GET /ubicaciones
    
    Returns:
        200: JSON con lista de todas las ubicaciones disponibles
        500: Error interno del servidor
    """
    ubicaciones = Ubicaciones.query.all()
    return jsonify({"status": "success", "data": ubicaciones_schema.dump(ubicaciones)})


@bp.route("/criticidades", methods=["GET"])
@jwt_required()
def get_criticidades():
    """
    Obtener el catálogo de niveles de criticidad.
    
    Endpoint: GET /criticidades
    
    Returns:
        200: JSON con lista de todos los niveles de criticidad
        500: Error interno del servidor
    """
    criticidades = CatalogoCriticidad.query.all()
    return jsonify(
        {"status": "success", "data": criticidades_schema.dump(criticidades)}
    )


