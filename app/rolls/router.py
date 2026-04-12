from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.rolls.schema import RolSchema
from app.rolls.services import rolls as RollsService

rolls_bp = Blueprint("rolls", __name__)


@rolls_bp.route("/roles", methods=["GET"])
@jwt_required()
def get_roles():
    schema = RolSchema()
    result = RollsService.get_all_roll(schema)
    if result.get("status") == "error":
        return jsonify(result), 500
    return jsonify(result), 200
