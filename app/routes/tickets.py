from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import joinedload
from datetime import datetime
from app import db
from app.models.soporteplus_models import (
    Tiquet, CatTiquet, EstadoTiquet, CatalogoCriticidad,
    Ubicaciones, Usuario, Comentarios, Documento
)
from marshmallow import Schema, fields, pre_load, ValidationError

bp = Blueprint('tickets', __name__)


class TiquetSchema(Schema):
    """
    Esquema de Marshmallow para la serialización y validación de Tickets.
    
    Define los campos que se exponen en la API y cómo se procesan los datos de entrada,
    incluyendo la conversión de formatos de fecha.
    """
    Id_Tiquet = fields.Int(dump_only=True)
    Categoria = fields.Int(allow_none=True)
    Tel_ext = fields.Str(allow_none=True)
    Ubicacion = fields.Int(allow_none=True)
    Criticidad = fields.Int(allow_none=True)
    Descripcion = fields.Str(allow_none=True)
    User_asig = fields.Int(allow_none=True)
    Estado = fields.Int(allow_none=True)
    Fecha_apertura = fields.Raw(allow_none=True)  # Manejado completamente en pre_load
    fecha_apertura_input = fields.Str(load_only=True, allow_none=True)  # Para recibir dd-mm-yyyy
    Fecha_cierre = fields.Raw(allow_none=True, dump_only=True)  # Solo para lectura, se establece automáticamente
    
    # Campos relacionados
    categoria_rel = fields.Nested('CatTiquetSchema', dump_only=True)
    ubicacion_rel = fields.Nested('UbicacionesSchema', dump_only=True)
    criticidad_rel = fields.Nested('CatalogoCriticidadSchema', dump_only=True)
    estado_rel = fields.Nested('EstadoTiquetSchema', dump_only=True)
    usuario_asignado = fields.Nested('UsuarioSchema', dump_only=True)
    
    @pre_load
    def convert_date_format(self, data, **kwargs):
        """
        Pre-procesamiento de datos antes de la validación.
        
        Convierte la fecha de entrada (dd-mm-yyyy) al formato compatible con la base de datos (date object).
        Si no se proporciona fecha, asigna la fecha actual.
        
        Args:
            data (dict): Datos crudos recibidos en la petición.
        """
        if 'fecha_apertura_input' in data and data['fecha_apertura_input']:
            try:
                # Convertir de dd-mm-yyyy a date object
                fecha_input = data['fecha_apertura_input']
                fecha_obj = datetime.strptime(fecha_input, '%d-%m-%Y').date()
                data['Fecha_apertura'] = fecha_obj
                # Remover el campo temporal
                del data['fecha_apertura_input']
            except ValueError:
                raise ValidationError('Fecha debe estar en formato dd-mm-yyyy', 'fecha_apertura_input')
        elif 'Fecha_apertura' not in data or data.get('Fecha_apertura') is None:
            # Si no se proporciona fecha, usar fecha actual
            data['Fecha_apertura'] = datetime.utcnow().date()
        return data


class CatTiquetSchema(Schema):
    """Schema para categorías de tickets"""
    Categoria = fields.Int(dump_only=True)
    Unidad_corresponde = fields.Str(allow_none=True)
    Nombre = fields.Str(allow_none=True)


class EstadoTiquetSchema(Schema):
    """Schema para estados de tickets"""
    ID_estado = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    Descripcion = fields.Str(allow_none=True)


class CatalogoCriticidadSchema(Schema):
    """Schema para criticidad"""
    ID_criti = fields.Int(dump_only=True)
    Nombre = fields.Str(allow_none=True)


class UbicacionesSchema(Schema):
    """Schema para ubicaciones"""
    Id_ubicacion = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    Zona = fields.Str(allow_none=True)


class UsuarioSchema(Schema):
    """Schema para usuarios"""
    ID_usuario = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    ID_Rol = fields.Int(allow_none=True)


class ComentarioSchema(Schema):
    """Schema para comentarios de tickets"""
    ID_comentario = fields.Int(dump_only=True)
    mensaje = fields.Str(allow_none=True)
    Tipo = fields.Str(allow_none=True)
    Satisfaccion = fields.Int(allow_none=True)
    usuario = fields.Int(allow_none=True)
    Id_Tiquet = fields.Int(allow_none=True)
    Fecha = fields.Raw(allow_none=True)

    # Extra útil para UI
    usuario_rel = fields.Nested('UsuarioSchema', dump_only=True)


# Instanciar schemas
tiquet_schema = TiquetSchema()
tiquets_schema = TiquetSchema(many=True)
cat_tiquet_schema = CatTiquetSchema()
cat_tiquets_schema = CatTiquetSchema(many=True)
estado_schema = EstadoTiquetSchema()
estados_schema = EstadoTiquetSchema(many=True)
criticidad_schema = CatalogoCriticidadSchema()
criticidades_schema = CatalogoCriticidadSchema(many=True)
ubicacion_schema = UbicacionesSchema()
ubicaciones_schema = UbicacionesSchema(many=True)

comentario_schema = ComentarioSchema()
comentarios_schema = ComentarioSchema(many=True)


@bp.route('/tickets', methods=['GET'])
@jwt_required()
def get_tickets():
    """
    Obtener todos los tickets registrados en el sistema.
    
    Utiliza 'joinedload' para realizar una carga ansiosa (eager loading) de las relaciones
    (categoría, ubicación, criticidad, usuario, estado) y evitar el problema de N+1 consultas.
    
    Returns:
        JSON: Lista de tickets serializados y el total de registros.
    """
    try:
        current_user_id = int(get_jwt_identity())
        current_user = Usuario.query.get(current_user_id)

        # Query base con relaciones
        query = Tiquet.query.options(
            joinedload(Tiquet.categoria_rel),
            joinedload(Tiquet.ubicacion_rel),
            joinedload(Tiquet.criticidad_rel),
            joinedload(Tiquet.usuario_asignado),
            joinedload(Tiquet.estado_rel)
        )

        # NOTA: Se elimina el filtro por User_asig para clientes para que puedan ver
        # los tickets que crearon aunque estén asignados a un técnico diferente.
        # Si se requiere filtrar por creador, se necesitaría un campo 'created_by' en la BD.
        
        tickets = query.all()
        
        return jsonify({
            'status': 'success',
            'data': tiquets_schema.dump(tickets),
            'total': len(tickets)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    """
    Obtener los detalles de un ticket específico por su ID.
    
    Args:
        ticket_id (int): ID del ticket a consultar.
        
    Returns:
        JSON: Datos del ticket o error 404 si no existe.
    """
    try:
        # Cargar ticket específico con todas sus relaciones
        ticket = Tiquet.query.options(
            joinedload(Tiquet.categoria_rel),
            joinedload(Tiquet.ubicacion_rel),
            joinedload(Tiquet.criticidad_rel),
            joinedload(Tiquet.usuario_asignado),
            joinedload(Tiquet.estado_rel)
        ).filter_by(Id_Tiquet=ticket_id).first()
        
        if not ticket:
            return jsonify({
                'status': 'error',
                'message': 'Ticket not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': tiquet_schema.dump(ticket)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/tickets/<int:ticket_id>/comentarios', methods=['GET'])
@jwt_required()
def get_ticket_comentarios(ticket_id):
    """Obtener comentarios de un ticket"""
    try:
        # Verificar que el ticket existe
        ticket = Tiquet.query.filter_by(Id_Tiquet=ticket_id).first()
        if not ticket:
            return jsonify({'status': 'error', 'message': 'Ticket not found'}), 404

        comentarios = (
            Comentarios.query.options(joinedload(Comentarios.usuario_rel))
            .filter_by(Id_Tiquet=ticket_id)
            .order_by(Comentarios.ID_comentario.asc())
            .all()
        )

        return jsonify({
            'status': 'success',
            'data': comentarios_schema.dump(comentarios),
            'total': len(comentarios)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/tickets/<int:ticket_id>/comentarios', methods=['POST'])
@jwt_required()
def add_ticket_comentario(ticket_id):
    """Agregar comentario (seguimiento) a un ticket"""
    try:
        data = request.get_json() or {}
        mensaje = (data.get('mensaje') or data.get('comentario') or '').strip()

        if not mensaje:
            return jsonify({'status': 'error', 'message': 'El mensaje es requerido'}), 400

        ticket = Tiquet.query.filter_by(Id_Tiquet=ticket_id).first()
        if not ticket:
            return jsonify({'status': 'error', 'message': 'Ticket not found'}), 404

        user_id = int(get_jwt_identity())
        user = Usuario.query.get(user_id)

        # Enum en BD: ('Usuario', 'tecnico')
        tipo = 'tecnico' if (user and user.ID_Rol == 2) or (user and user.is_admin) else 'Usuario'

        comentario = Comentarios(
            mensaje=mensaje,
            Tipo=tipo,
            usuario=user_id,
            Id_Tiquet=ticket_id,
            Fecha=datetime.utcnow().date(),
        )

        db.session.add(comentario)
        db.session.commit()

        comentario_db = Comentarios.query.options(joinedload(Comentarios.usuario_rel)).get(comentario.ID_comentario)

        return jsonify({
            'status': 'success',
            'message': 'Comentario agregado',
            'data': comentario_schema.dump(comentario_db)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/tickets', methods=['POST'])
@jwt_required()
def create_ticket():
    """
    Crear un nuevo ticket en el sistema.
    
    Valida los datos de entrada utilizando TiquetSchema.
    
    Returns:
        JSON: El ticket creado con sus datos y relaciones, o lista de errores de validación.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No se proporcionaron datos'
            }), 400
        
        # Forzar la asignación del ticket al usuario que lo crea si es un cliente (Rol 3)
        current_user_id = int(get_jwt_identity())
        current_user = Usuario.query.get(current_user_id)

        # Si no especifican un técnico (User_asig), se le asigna al usuario actual por defecto.
        if 'User_asig' not in data or not data.get('User_asig'):
            data['User_asig'] = current_user_id

        # Validar y transformar datos usando el schema
        try:
            validated_data = tiquet_schema.load(data)
        except ValidationError as err:
            return jsonify({
                'status': 'error',
                'message': 'Datos inválidos',
                'errors': err.messages
            }), 400
        
        # Crear ticket con datos validados
        ticket = Tiquet(**validated_data)
        db.session.add(ticket)
        db.session.commit()
        
        # Cargar ticket con relaciones para la respuesta
        ticket_with_relations = Tiquet.query.options(
            joinedload(Tiquet.categoria_rel),
            joinedload(Tiquet.ubicacion_rel),
            joinedload(Tiquet.criticidad_rel),
            joinedload(Tiquet.usuario_asignado),
            joinedload(Tiquet.estado_rel)
        ).filter_by(Id_Tiquet=ticket.Id_Tiquet).first()
        
        return jsonify({
            'status': 'success',
            'message': 'Ticket creado exitosamente',
            'data': tiquet_schema.dump(ticket_with_relations)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error interno del servidor: {str(e)}'
        }), 500


@bp.route('/tickets/<int:ticket_id>', methods=['PUT'])
@jwt_required()
def update_ticket(ticket_id):
    """
    Actualizar la información de un ticket existente.
    
    Args:
        ticket_id (int): ID del ticket a actualizar.
        
    Returns:
        JSON: Datos del ticket actualizado.
    """
    try:
        ticket = Tiquet.query.get_or_404(ticket_id)
        data = request.get_json()
        
        # Validar datos
        errors = tiquet_schema.validate(data, partial=True)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Datos inválidos',
                'errors': errors
            }), 400
        
        # Obtener usuario actual para verificar permisos
        current_user_id = int(get_jwt_identity())
        current_user = Usuario.query.get(current_user_id)

        # Validar que el usuario sea dueño del ticket o admin (si es Rol 3)
        # COMENTADO: Permitir que el usuario edite el ticket (para agregar comentarios)
        # aunque ya esté asignado a un técnico.
        # if current_user and current_user.ID_Rol == 3 and ticket.User_asig != current_user_id:
        #     return jsonify({
        #         'status': 'error',
        #         'message': 'No tienes permiso para editar este ticket'
        #     }), 403

        # Actualizar campos
        for key, value in data.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Ticket actualizado exitosamente',
            'data': tiquet_schema.dump(ticket)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/tickets/<int:ticket_id>', methods=['DELETE'])
@jwt_required()
def delete_ticket(ticket_id):
    """
    Eliminar un ticket del sistema.
    
    Args:
        ticket_id (int): ID del ticket a eliminar.
        
    Returns:
        JSON: Mensaje de confirmación.
    """
    try:
        ticket = Tiquet.query.get_or_404(ticket_id)
        
        # Eliminar registros relacionados primero si es necesario
      
        db.session.delete(ticket)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Ticket {ticket_id} eliminado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error al eliminar ticket: {str(e)}'
        }), 500


@bp.route('/tickets/<int:ticket_id>/close', methods=['PUT'])
@jwt_required()
def close_ticket(ticket_id):
    """
    Cerrar un ticket formalmente.
    
    Esta acción busca el estado 'Cerrado' en la base de datos, actualiza el estado del ticket
    y establece la fecha de cierre actual automáticamente.
    
    Args:
        ticket_id (int): ID del ticket a cerrar.
    """
    try:
        # Buscar el ticket
        ticket = Tiquet.query.get_or_404(ticket_id)
        
        # Buscar el estado "cerrado" 
        estado_cerrado = EstadoTiquet.query.filter_by(Nombre='Cerrado').first()
        if not estado_cerrado:
            # Si no encuentra "Cerrado", buscar por variaciones comunes
            estado_cerrado = EstadoTiquet.query.filter(
                EstadoTiquet.Nombre.ilike('%cerrado%') | 
                EstadoTiquet.Nombre.ilike('%closed%') |
                EstadoTiquet.Nombre.ilike('%finalizado%')
            ).first()
        
        if not estado_cerrado:
            return jsonify({
                'status': 'error',
                'message': 'No se encontró un estado de "Cerrado" en el sistema'
            }), 400
        
        # Verificar si el ticket ya está cerrado
        if ticket.Estado == estado_cerrado.ID_estado and ticket.Fecha_cierre:
            return jsonify({
                'status': 'warning',
                'message': 'El ticket ya está cerrado',
                'data': {
                    'Id_Tiquet': ticket.Id_Tiquet,
                    'Estado': ticket.Estado,
                    'Fecha_cierre': ticket.Fecha_cierre.strftime('%d-%m-%Y') if ticket.Fecha_cierre else None
                }
            })
        
        # Cerrar el ticket
        ticket.Estado = estado_cerrado.ID_estado
        ticket.Fecha_cierre = datetime.utcnow().date()
        
        db.session.commit()
        
        # Cargar relaciones para la respuesta
        ticket_with_relations = Tiquet.query.options(
            joinedload(Tiquet.categoria_rel),
            joinedload(Tiquet.ubicacion_rel), 
            joinedload(Tiquet.criticidad_rel),
            joinedload(Tiquet.estado_rel),
            joinedload(Tiquet.usuario_asignado)
        ).get(ticket_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Ticket {ticket_id} cerrado exitosamente',
            'data': {
                'Id_Tiquet': ticket_with_relations.Id_Tiquet,
                'Estado': ticket_with_relations.Estado,
                'Estado_nombre': ticket_with_relations.estado_rel.Nombre if ticket_with_relations.estado_rel else None,
                'Fecha_apertura': ticket_with_relations.Fecha_apertura.strftime('%d-%m-%Y') if ticket_with_relations.Fecha_apertura else None,
                'Fecha_cierre': ticket_with_relations.Fecha_cierre.strftime('%d-%m-%Y') if ticket_with_relations.Fecha_cierre else None,
                'Descripcion': ticket_with_relations.Descripcion
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error al cerrar ticket: {str(e)}'
        }), 500


# Rutas para catálogos
@bp.route('/categorias', methods=['GET'])
@jwt_required()
def get_categorias():
    """Obtener el catálogo completo de categorías de tickets."""
    categorias = CatTiquet.query.all()
    return jsonify({
        'status': 'success',
        'data': cat_tiquets_schema.dump(categorias)
    })


@bp.route('/categorias', methods=['POST'])
@jwt_required()
def create_categoria():
    """Crear una nueva categoría en el catálogo."""
    try:
        # Validar datos de entrada
        categoria_data = cat_tiquet_schema.load(request.json)
        
        # Crear nueva categoría
        nueva_categoria = CatTiquet(
            Unidad_corresponde=categoria_data.get('Unidad_corresponde'),
            Nombre=categoria_data.get('Nombre')
        )
        
        db.session.add(nueva_categoria)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Categoría creada exitosamente',
            'data': cat_tiquet_schema.dump(nueva_categoria)
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': 'Datos inválidos',
            'errors': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error al crear categoría: {str(e)}'
        }), 500


@bp.route('/categorias/<int:categoria_id>', methods=['PUT'])
@jwt_required()
def update_categoria(categoria_id):
    """Actualizar los datos de una categoría existente."""
    try:
        # Buscar la categoría
        categoria = CatTiquet.query.get(categoria_id)
        if not categoria:
            return jsonify({
                'status': 'error',
                'message': 'Categoría no encontrada'
            }), 404
        
        # Validar datos de entrada
        categoria_data = cat_tiquet_schema.load(request.json, partial=True)
        
        # Actualizar campos
        if 'Unidad_corresponde' in categoria_data:
            categoria.Unidad_corresponde = categoria_data['Unidad_corresponde']
        if 'Nombre' in categoria_data:
            categoria.Nombre = categoria_data['Nombre']
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Categoría actualizada exitosamente',
            'data': cat_tiquet_schema.dump(categoria)
        })
        
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': 'Datos inválidos',
            'errors': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error al actualizar categoría: {str(e)}'
        }), 500


@bp.route('/categorias/<int:categoria_id>', methods=['DELETE'])
@jwt_required()
def delete_categoria(categoria_id):
    """Eliminar una categoría (si no está en uso)."""
    try:
        # Buscar la categoría
        categoria = CatTiquet.query.get(categoria_id)
        if not categoria:
            return jsonify({
                'status': 'error',
                'message': 'Categoría no encontrada'
            }), 404
        
        # Verificar si la categoría está siendo usada por algún ticket
        tickets_usando_categoria = Tiquet.query.filter_by(Categoria=categoria_id).first()
        if tickets_usando_categoria:
            return jsonify({
                'status': 'error',
                'message': 'No se puede eliminar la categoría porque está siendo utilizada por uno o más tickets'
            }), 400
        
        db.session.delete(categoria)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Categoría eliminada exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error al eliminar categoría: {str(e)}'
        }), 500


@bp.route('/estados', methods=['GET'])
@jwt_required()
def get_estados():
    """Obtener el catálogo de estados posibles para un ticket."""
    estados = EstadoTiquet.query.all()
    return jsonify({
        'status': 'success',
        'data': estados_schema.dump(estados)
    })


@bp.route('/criticidades', methods=['GET'])
@jwt_required()
def get_criticidades():
    """Obtener el catálogo de niveles de criticidad."""
    criticidades = CatalogoCriticidad.query.all()
    return jsonify({
        'status': 'success',
        'data': criticidades_schema.dump(criticidades)
    })


@bp.route('/ubicaciones', methods=['GET'])
@jwt_required()
def get_ubicaciones():
    """Obtener el catálogo de ubicaciones disponibles."""
    ubicaciones = Ubicaciones.query.all()
    return jsonify({
        'status': 'success',
        'data': ubicaciones_schema.dump(ubicaciones)
    })


@bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """
    Obtener estadísticas generales para el panel de control (Dashboard).
    
    Calcula totales de tickets, desglose por estado y por criticidad
    para generar gráficas y reportes.
    """
    try:
        total_tickets = Tiquet.query.count()
        tickets_abiertos = Tiquet.query.join(EstadoTiquet).filter(
            EstadoTiquet.Nombre != 'Cerrado'
        ).count()
        tickets_cerrados = total_tickets - tickets_abiertos
        
        # Tickets por estado
        tickets_por_estado = db.session.query(
            EstadoTiquet.Nombre,
            db.func.count(Tiquet.Id_Tiquet)
        ).outerjoin(Tiquet).group_by(EstadoTiquet.ID_estado).all()
        
        # Tickets por criticidad
        tickets_por_criticidad = db.session.query(
            CatalogoCriticidad.Nombre,
            db.func.count(Tiquet.Id_Tiquet)
        ).outerjoin(Tiquet).group_by(CatalogoCriticidad.ID_criti).all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_tickets': total_tickets,
                'tickets_abiertos': tickets_abiertos,
                'tickets_cerrados': tickets_cerrados,
                'tickets_por_estado': [
                    {'estado': estado, 'cantidad': cantidad}
                    for estado, cantidad in tickets_por_estado
                ],
                'tickets_por_criticidad': [
                    {'criticidad': criticidad, 'cantidad': cantidad}
                    for criticidad, cantidad in tickets_por_criticidad
                ]
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500