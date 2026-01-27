import os
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import Schema, ValidationError, fields, pre_load
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app import db
from app.models.soporteplus_models import (
    CatalogoCriticidad,
    CatTiquet,
    Documento,
    EstadoTiquet,
    Tiquet,
    Ubicaciones,
    Usuario,
)

bp = Blueprint("tickets", __name__)

# --- SCHEMAS DE MARSHMALLOW ---


class DocumentoSchema(Schema):
    """Schema para serializar documentos adjuntos"""

    id = fields.Int(dump_only=True)
    nombre_original = fields.Str(dump_only=True)
    ruta_relativa = fields.Str(dump_only=True)
    mimetype = fields.Str(dump_only=True)
    tamano = fields.Int(dump_only=True)
    fecha_creacion = fields.DateTime(dump_only=True)
    Id_Tiquet = fields.Int(dump_only=True)  # Este sí existe


class TiquetSchema(Schema):
    """Schema para serializar tickets"""

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
    Categoria = fields.Int(dump_only=True)
    Unidad_corresponde = fields.Str(allow_none=True)
    Nombre = fields.Str(allow_none=True)


class EstadoTiquetSchema(Schema):
    ID_estado = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    Descripcion = fields.Str(allow_none=True)


class CatalogoCriticidadSchema(Schema):
    ID_criti = fields.Int(dump_only=True)
    Nombre = fields.Str(allow_none=True)


class UbicacionesSchema(Schema):
    Id_ubicacion = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    Zona = fields.Str(allow_none=True)


class UsuarioSchema(Schema):
    ID_usuario = fields.Int(dump_only=True)
    Nombre = fields.Str(required=True)
    ID_Rol = fields.Int(allow_none=True)


# Instancias
tiquet_schema = TiquetSchema()
tiquets_schema = TiquetSchema(many=True)
cat_tiquet_schema = CatTiquetSchema()
cat_tiquets_schema = CatTiquetSchema(many=True)
estados_schema = EstadoTiquetSchema(many=True)
criticidades_schema = CatalogoCriticidadSchema(many=True)
ubicaciones_schema = UbicacionesSchema(many=True)

documento_schema = DocumentoSchema()
# --- RUTAS DE TICKETS ---


@bp.route("/tickets", methods=["GET"])
@jwt_required()
def get_tickets():
    try:
        tickets = Tiquet.query.options(
            joinedload(Tiquet.categoria_rel),
            joinedload(Tiquet.ubicacion_rel),
            joinedload(Tiquet.criticidad_rel),
            joinedload(Tiquet.usuario_asignado),
            joinedload(Tiquet.estado_rel),
            joinedload(Tiquet.documentos),
        ).all()
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


@bp.route("/tickets", methods=["POST"])
@jwt_required()
def create_ticket():
    try:
        data = request.get_json()
        validated_data = tiquet_schema.load(data)
        ticket = Tiquet(**validated_data)
        db.session.add(ticket)
        db.session.commit()
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
    try:
        # 1. Buscar el ticket existente
        ticket = Tiquet.query.get_or_404(ticket_id)

        # 2. Obtener los datos que envía React
        data = request.get_json()

        # 3. Actualizar solo los campos que vengan en la petición
        if "Descripcion" in data:
            ticket.Descripcion = data["Descripcion"]
        if "Categoria" in data:
            ticket.Categoria = data["Categoria"]
        if "Ubicacion" in data:
            ticket.Ubicacion = data["Ubicacion"]
        if "Criticidad" in data:
            ticket.Criticidad = data["Criticidad"]
        if "Estado" in data:
            ticket.Estado = data["Estado"]
        if "User_asig" in data:
            ticket.User_asig = data["User_asig"]

        # Nota: Si manejas fecha de cierre al cambiar estado a "Cerrado", agrégalo aquí

        # 4. Guardar cambios
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
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/tickets/<int:ticket_id>/upload", methods=["POST"])
@jwt_required()
def upload_file(ticket_id):
    """Buzón para recibir archivos adjuntos de React"""
    try:
        # 1. Buscar el ticket
        ticket = Tiquet.query.get_or_404(ticket_id)

        # 2. Validar que venga el archivo
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No hay archivo"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"status": "error", "message": "Sin selección"}), 400

        # 3. Guardar archivo físicamente
        nombre_original = secure_filename(file.filename)
        # Generar nombre único
        nombre_almacenado = f"{uuid.uuid4().hex}{os.path.splitext(nombre_original)[1]}"

        ruta_carpeta = current_app.config["UPLOAD_FOLDER"]
        if not os.path.exists(ruta_carpeta):
            os.makedirs(ruta_carpeta)

        ruta_completa = os.path.join(ruta_carpeta, nombre_almacenado)
        file.save(ruta_completa)

        # 4. Guardar registro en BD
        nuevo_doc = Documento(
            nombre_original=nombre_original,
            nombre_almacenado=nombre_almacenado,
            ruta_relativa=f"static/uploads/{nombre_almacenado}",
            mimetype=file.mimetype,
            tamano=os.path.getsize(ruta_completa),
            Id_Tiquet=ticket_id,
        )
        db.session.add(nuevo_doc)
        db.session.commit()
        return jsonify(
            {"status": "success", "data": documento_schema.dump(nuevo_doc)}
        ), 201

    except Exception as e:
        import traceback

        print("\n\n🔴🔴🔴 ERROR EN UPLOAD 🔴🔴🔴")
        traceback.print_exc()
        print("🔴🔴🔴 FIN ERROR 🔴🔴🔴\n\n")
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ESTADÍSTICAS ---


@bp.route("/dashboard/stats", methods=["GET"])
@jwt_required()
def get_dashboard_stats():
    try:
        total = Tiquet.query.count()
        por_estado = (
            db.session.query(EstadoTiquet.Nombre, db.func.count(Tiquet.Id_Tiquet))
            .outerjoin(Tiquet)
            .group_by(EstadoTiquet.ID_estado)
            .all()
        )
        return jsonify(
            {
                "status": "success",
                "data": {
                    "total": total,
                    "stats_estado": [
                        {"estado": e, "cantidad": c} for e, c in por_estado
                    ],
                },
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- CATÁLOGOS ---


@bp.route("/categorias", methods=["GET"])
@jwt_required()
def get_categorias():
    return jsonify(
        {"status": "success", "data": cat_tiquets_schema.dump(CatTiquet.query.all())}
    )


@bp.route("/estados", methods=["GET"])
@jwt_required()
def get_estados():
    return jsonify(
        {"status": "success", "data": estados_schema.dump(EstadoTiquet.query.all())}
    )


@bp.route("/ubicaciones", methods=["GET"])
@jwt_required()
def get_ubicaciones():
    return jsonify(
        {"status": "success", "data": ubicaciones_schema.dump(Ubicaciones.query.all())}
    )


@bp.route("/criticidades", methods=["GET"])
@jwt_required()
def get_criticidades():
    return jsonify(
        {
            "status": "success",
            "data": criticidades_schema.dump(CatalogoCriticidad.query.all()),
        }
    )


@bp.route("/documents/<int:doc_id>", methods=["DELETE"])
@jwt_required()
def delete_document(doc_id):
    try:
        # 1. Buscar el documento
        doc = Documento.query.get_or_404(doc_id)

        # 2. Construir la ruta física del archivo para borrarlo
        # Usamos current_app.root_path para llegar a la carpeta 'app'
        archivo_fisico = os.path.join(current_app.root_path, doc.ruta_relativa)

        # 3. Borrar el archivo del disco (si existe)
        if os.path.exists(archivo_fisico):
            os.remove(archivo_fisico)

        # 4. Borrar el registro de la base de datos
        db.session.delete(doc)
        db.session.commit()

        return jsonify({"status": "success", "message": "Archivo eliminado"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
