import os
import socket
import platform
import logging
from datetime import datetime, timezone
from flask import Flask, jsonify, request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Application start time
START_TIME = datetime.now(timezone.utc)

def get_uptime():
    """Calculation of the application's operating time."""
    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return {
        'seconds': seconds,
        'human': f"{hours} hours, {minutes} minutes"
    }

def get_system_info():
    """Collect system information."""
    return {
        'hostname': socket.gethostname(),
        'platform': platform.system(),
        'platform_version': get_platform_version(),
        'architecture': platform.machine(),
        'cpu_count': os.cpu_count(),
        'python_version': platform.python_version()
    }

@app.route('/')
def index():
    """Main endpoint - service and system information."""
    uptime = get_uptime()
    
    response = {
        'service': {
            'name': 'devops-info-service',
            'version': '1.0.0',
            'description': 'DevOps course info service',
            'framework': 'Flask'
        },
        'system': get_system_info(),
        'runtime': {
            'uptime_seconds': uptime['seconds'],
            'uptime_human': uptime['human'],
            'current_time': datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            'timezone': 'UTC'
        },
        'request': {
            'client_ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'method': request.method,
            'path': request.path
        },
        'endpoints': [
            {'path': '/', 'method': 'GET', 'description': 'Service information'},
            {'path': '/health', 'method': 'GET', 'description': 'Health check'}
        ]
    }
    
    logger.info("Request %s %s from %s", request.method, request.path, request.remote_addr)
    return jsonify(response)

@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    logger.info("Request %s %s from %s", request.method, request.path, request.remote_addr)
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        'uptime_seconds': get_uptime()['seconds']
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Endpoint does not exist'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500

def get_platform_version():
    """Return a platform version."""
    try:
        if hasattr(platform, "freedesktop_os_release"):
            info = platform.freedesktop_os_release()
            if info.get("PRETTY_NAME"):
                return info["PRETTY_NAME"]
    except Exception:
        pass
    return platform.platform()


if __name__ == '__main__':
    logger.info(f'Starting DevOps Info Service on {HOST}:{PORT}')
    app.run(host=HOST, port=PORT, debug=DEBUG)