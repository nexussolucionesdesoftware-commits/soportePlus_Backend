from flask import Blueprint, jsonify

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Endpoint principal de la API"""
    return jsonify({
        'message': 'SoportePlus Backend API',
        'version': '1.0.0',
        'status': 'running'
    })


@main_bp.route('/health')
def health_check():
    """Endpoint de estado de salud"""
    return jsonify({
        'status': 'healthy',
        'message': 'Service is running normally'
    })