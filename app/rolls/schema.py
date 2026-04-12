from marshmallow import Schema, fields


class RolSchema(Schema):
    ID_Rol = fields.Int(dump_only=True)
    Nombre = fields.Str(dump_only=True)
