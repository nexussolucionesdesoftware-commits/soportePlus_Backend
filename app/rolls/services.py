from app.models.soporteplus_models import Rol
from sqlalchemy import select
from app import db

class rolls:
    @staticmethod
    def get_all_roll(roll_schema):
        try:
            roles = db.session.execute(select(Rol)).scalars().all()
            return {
                "status": "success",
                "data": roll_schema.dump(roles, many=True),
                "count": len(roles),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al obtener roles: {str(e)}",
            }
