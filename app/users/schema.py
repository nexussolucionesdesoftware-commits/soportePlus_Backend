from marshmallow import Schema, fields
from marshmallow import validate


class UpdateUserSchema(Schema):
    nombre = fields.Str(
        required=False,
        validate=validate.Length(min=3),
        load_default=None,
    )
    email = fields.Email(required=False, load_default=None)
    password = fields.Str(
        required=False,
        validate=validate.Length(min=6),
        load_default=None,
    )
    ID_Rol = fields.Int(
        required=False,
        validate=validate.OneOf(
            [1, 2, 3],
            error="Rol inválido. Valores permitidos: 1=admin, 2=tecnico, 3=usuario",
        ),
        load_default=None,
    )


class RolSchema(Schema):
    ID_Rol = fields.Int(dump_only=True)
    Nombre = fields.Str(dump_only=True)
