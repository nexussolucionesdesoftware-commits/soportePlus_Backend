from marshmallow import Schema, fields


class RegisterSchema(Schema):
    nombre = fields.Str(required=True, validate=lambda x: len(x) >= 3)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 6)
    ID_Rol = fields.Int(
        required=False,
        load_default=2,
        validate=lambda x: x in [1, 2, 3] if x is not None else True,
    )


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)
