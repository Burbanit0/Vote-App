import eventlet
eventlet.monkey_patch()  # MUST happen before any other imports for WebSocket to work

from app import create_app, socketio  # noqa: E402

app = create_app()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=4433, debug=False, use_reloader=False)
