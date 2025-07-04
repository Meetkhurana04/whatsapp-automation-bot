import os
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

from whatsapp_bot import WhatsAppBot

# Configure basic logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("whatsapp_sender.app")

# Environment variables for optional configuration
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
API_KEY = os.getenv("API_KEY")  # Optional simple API key protection
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

# Directory to store session data
SESSIONS_DIR = Path("./sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

# Dictionary to store active bot instances
bot_instances = {}
app = Flask(__name__)

def require_api_key(f):
    """Decorator for API key authentication"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if API_KEY:
            provided_key = request.headers.get("X-API-KEY")
            if not provided_key or provided_key != API_KEY:
                return jsonify({"success": False, "error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return wrapper

def get_or_create_bot(device_id='default', force_new=False):
    """Get or create a bot instance for the given device ID"""
    if not force_new and device_id in bot_instances:
        return bot_instances[device_id]
        
    # Create new bot instance with device-specific profile
    profile_dir = SESSIONS_DIR / device_id
    bot = WhatsAppBot(headless=HEADLESS, profile_dir=profile_dir)
    bot_instances[device_id] = bot
    return bot

def cleanup_old_sessions():
    """Clean up old and inactive sessions"""
    current_time = time.time()
    timeout_seconds = SESSION_TIMEOUT_MINUTES * 60
    
    for device_id, bot in list(bot_instances.items()):
        try:
            # Check if session is too old
            if current_time - bot.last_activity > timeout_seconds:
                logger.info(f"Cleaning up old session for device: {device_id}")
                bot.close()
                del bot_instances[device_id]
        except Exception as e:
            logger.error(f"Error cleaning up session for {device_id}: {e}")

@app.route("/initialize/<device_id>", methods=["POST"])
@require_api_key
def initialize_session(device_id='default'):
    """Initialize or get existing WhatsApp session for a device"""
    try:
        logger.info(f"Initializing session for device: {device_id}")
        
        # Check existing session first
        bot = get_or_create_bot(device_id)
        
        # Check if already authenticated
        if bot.is_authenticated:
            logger.info(f"Device {device_id} already authenticated, reusing session")
            return jsonify({
                'success': True,
                'message': 'Session already authenticated',
                'device_id': device_id,
                'qr_required': False,
                'timestamp': datetime.now().isoformat()
            })
        
        # Initialize new session
        result = bot.initialize_session()
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Session initialized successfully',
                'device_id': device_id,
                'qr_required': result.get('qr_required', False),
                'qr_url': f'/qr/{device_id}' if result.get('qr_required') else None,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error initializing session'),
                'device_id': device_id,
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Error initializing session: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error initializing session: {str(e)}',
            'device_id': device_id,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route("/qr/<device_id>")
@require_api_key
def get_qr_code(device_id):
    """Get the QR code for a device session"""
    try:
        bot = get_or_create_bot(device_id)
        qr_path = bot.get_qr_code_path()
        if qr_path and qr_path.exists():
            return send_from_directory(qr_path.parent, qr_path.name)
        return jsonify({"success": False, "error": "QR code not available"}), 404
    except Exception as e:
        logger.error(f"Error getting QR code: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/send/<device_id>", methods=["POST"])
@require_api_key
def send_message(device_id='default'):
    """Send a message using the specified device session"""
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    message = data.get("message")

    if not phone or not message:
        return jsonify({"success": False, "error": "'phone' and 'message' fields are required"}), 400

    try:
        bot = get_or_create_bot(device_id)
        success = bot.send_message(phone, message)
        
        if success:
            return jsonify({
                "success": True,
                "device_id": device_id,
                "phone": phone,
                "timestamp": datetime.now().isoformat()
            })
        return jsonify({
            "success": False,
            "error": "Failed to send message",
            "device_id": device_id,
            "timestamp": datetime.now().isoformat()
        }), 500
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "device_id": device_id,
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/sessions/<device_id>", methods=["DELETE"])
@require_api_key
def delete_session(device_id):
    """Delete a device session"""
    try:
        if device_id in bot_instances:
            bot_instances[device_id].close()
            del bot_instances[device_id]
        # Optionally: Delete the session directory
        # import shutil
        # session_dir = SESSIONS_DIR / device_id
        # if session_dir.exists():
        #     shutil.rmtree(session_dir)
        return jsonify({"success": True, "message": f"Session {device_id} deleted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/healthz", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(bot_instances)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
