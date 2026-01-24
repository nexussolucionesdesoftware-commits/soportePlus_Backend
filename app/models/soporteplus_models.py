import uuid
from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class CatTiquet(db.Model):
    """Modelo para Cat_tiquet - Categorías de tickets"""

    __tablename__ = "Cat_tiquet"

    Categoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Unidad_corresponde = db.Column(db.String(255), nullable=True)
    Nombre = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<CatTiquet {self.Nombre}>"


class CatalogoCriticidad(db.Model):
    """Modelo para Catalogo_criticidad - Niveles de criticidad"""

    __tablename__ = "Catalogo_criticidad"

    ID_criti = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<CatalogoCriticidad {self.Nombre}>"


class NivelSatisfaccion(db.Model):
    """Modelo para Nivel_de_Satisfaccion - Niveles de satisfacción"""

    __tablename__ = "Nivel_de_Satisfaccion"

    ID_nivel = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<NivelSatisfaccion {self.Nombre}>"


class Rol(db.Model):
    """Modelo para Rol - Roles del sistema"""

    __tablename__ = "Rol"

    ID_Rol = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Rol {self.Nombre}>"


class Permiso(db.Model):
    """Modelo para Permiso - Permisos del sistema"""

    __tablename__ = "Permiso"

    ID_Permiso = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Permiso {self.Nombre}>"


class RolPermiso(db.Model):
    """Modelo para Rol_Permiso - Relación entre roles y permisos"""

    __tablename__ = "Rol_Permiso"

    ID_RolPermiso = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ID_Rol = db.Column(db.Integer, db.ForeignKey("Rol.ID_Rol"), nullable=True)
    ID_Permiso = db.Column(
        db.Integer, db.ForeignKey("Permiso.ID_Permiso"), nullable=True
    )

    def __repr__(self):
        return f"<RolPermiso {self.ID_RolPermiso}>"


class Ubicaciones(db.Model):
    """Modelo para Ubicaciones - Ubicaciones físicas"""

    __tablename__ = "Ubicaciones"

    Id_ubicacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Ubicaciones {self.Nombre}>"


class EstadoTiquet(db.Model):
    """Modelo para Estado_tiquet - Estados de tickets"""

    __tablename__ = "Estado_tiquet"

    ID_estado = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(255), nullable=True)
    Descripcion = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<EstadoTiquet {self.Nombre}>"


class Usuario(db.Model):
    """Modelo para Usuario - Usuarios del sistema original"""

    __tablename__ = "Usuario"

    ID_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(255), nullable=False)
    # Apellido = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    ID_Rol = db.Column(db.Integer, db.ForeignKey("Rol.ID_Rol"), nullable=True)
    password = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        """Establecer contraseña hasheada"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password, password)

    def get_tokens(self):
        """Generar tokens JWT para el usuario"""
        access_token = create_access_token(
            identity=str(self.ID_usuario), expires_delta=timedelta(hours=1)
        )
        refresh_token = create_refresh_token(
            identity=str(self.ID_usuario), expires_delta=timedelta(days=30)
        )
        return {"access_token": access_token, "refresh_token": refresh_token}

    @property
    def is_admin(self):
        """Verificar si el usuario es administrador (rol 1)"""
        return self.ID_Rol == 1

    @property
    def is_active(self):
        """Verificar si el usuario está activo"""
        return True

    def save(self):
        """Guardar el usuario en la base de datos"""
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f"<Usuario {self.Nombre}>"


class Tiquet(db.Model):
    """Modelo para Tiquet - Tickets del sistema"""

    __tablename__ = "Tiquet"

    Id_Tiquet = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Categoria = db.Column(
        db.Integer, db.ForeignKey("Cat_tiquet.Categoria"), nullable=True
    )
    Tel_ext = db.Column(db.String(8), nullable=True)
    Ubicacion = db.Column(
        db.Integer, db.ForeignKey("Ubicaciones.Id_ubicacion"), nullable=True
    )
    Criticidad = db.Column(
        db.Integer, db.ForeignKey("Catalogo_criticidad.ID_criti"), nullable=True
    )
    Descripcion = db.Column(db.String(500), nullable=True)
    User_asig = db.Column(
        db.Integer, db.ForeignKey("Usuario.ID_usuario"), nullable=True
    )
    Estado = db.Column(
        db.Integer, db.ForeignKey("Estado_tiquet.ID_estado"), nullable=True
    )
    Fecha_apertura = db.Column(db.Date, nullable=True, default=datetime.utcnow().date())
    Fecha_cierre = db.Column(db.Date, nullable=True)  # Fecha de cierre del ticket

    # Relaciones con backref
    categoria_rel = db.relationship("CatTiquet", backref="tiquets")
    ubicacion_rel = db.relationship("Ubicaciones", backref="tiquets")
    criticidad_rel = db.relationship("CatalogoCriticidad", backref="tiquets")
    usuario_asignado = db.relationship("Usuario", backref="tiquets_asignados")
    estado_rel = db.relationship("EstadoTiquet", backref="tiquets")

    def __repr__(self):
        return f"<Tiquet {self.Id_Tiquet}>"


class Comentarios(db.Model):
    """Modelo para Comentarios - Comentarios de tickets"""

    __tablename__ = "Comentarios"

    ID_comentario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mensaje = db.Column(db.String(255), nullable=True)
    Tipo = db.Column(db.Enum("Usuario", "tecnico"), nullable=True)
    Satisfaccion = db.Column(db.Integer, nullable=True)
    usuario = db.Column(db.Integer, db.ForeignKey("Usuario.ID_usuario"), nullable=True)
    Id_Tiquet = db.Column(db.Integer, db.ForeignKey("Tiquet.Id_Tiquet"), nullable=True)
    Fecha = db.Column(db.Date, nullable=True)

    # Relaciones
    usuario_rel = db.relationship("Usuario", backref="comentarios")
    tiquet_rel = db.relationship("Tiquet", backref="comentarios")

    def __repr__(self):
        return f"<Comentarios {self.ID_comentario}>"


class LogTransaccional(db.Model):
    """Modelo para Log_transaccional - Log de transacciones"""

    __tablename__ = "Log_transaccional"

    Id_log = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Usuario = db.Column(db.Integer, db.ForeignKey("Usuario.ID_usuario"), nullable=True)
    Tiquet = db.Column(db.Integer, db.ForeignKey("Tiquet.Id_Tiquet"), nullable=True)
    Accion = db.Column(db.String(255), nullable=True)
    # Fecha = db.Column(db.DateTime, default=datetime.utcnow)  # Comentado temporalmente - verificar nombre real en BD

    # Relaciones
    usuario_rel = db.relationship("Usuario", backref="logs")
    tiquet_rel = db.relationship("Tiquet", backref="logs")

    def __repr__(self):
        return f"<LogTransaccional {self.Id_log}>"


# Clase para guardar los documentos asociados a un ticket o usuario
class Documento(db.Model):
    __tablename__ = "Documentos"

    id = db.Column(db.Integer, primary_key=True)
    nombre_original = db.Column(db.String(255), nullable=False)
    # Nombre único en el disco duro para evitar sobrescribir archivos
    nombre_almacenado = db.Column(db.String(255), unique=True, nullable=False)
    ruta_relativa = db.Column(db.String(500), nullable=False)
    mimetype = db.Column(db.String(100))
    tamano = db.Column(db.Integer)

    # Relación con la tabla Tiquet
    Id_Tiquet = db.Column(db.Integer, db.ForeignKey("Tiquet.Id_Tiquet"), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("Usuario.ID_usuario"), nullable=True
    )
    usuario = db.relationship("Usuario", backref="documentos")
    tiquet = db.relationship("Tiquet", backref="documentos")
    # Relación con la tabla LogTransaccional
    log_id = db.Column(
        db.Integer, db.ForeignKey("LogTransaccional.Id_log"), nullable=True
    )
    log = db.relationship("LogTransaccional", backref="documentos")

    def __repr__(self):
        return f"<Documento {self.nombre_original}>"
