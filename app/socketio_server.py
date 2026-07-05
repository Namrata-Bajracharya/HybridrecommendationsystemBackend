import socketio
from app.utils.security import decode_access_token, TokenError
from app.models.user import User
from app.db.database import SessionLocal

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    cors_credentials=True,
)


@sio.event
async def connect(sid, environ, auth):
    token = None
    if auth and "token" in auth:
        token = auth["token"]
    elif "HTTP_AUTHORIZATION" in environ:
        parts = environ["HTTP_AUTHORIZATION"].split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    elif "token" in environ.get("QUERY_STRING", ""):
        from urllib.parse import parse_qs
        qs = parse_qs(environ.get("QUERY_STRING", ""))
        token = qs.get("token", [None])[0]

    if not token:
        return True

    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            return True
        user_id = int(sub)
        db = SessionLocal()
        try:
            user = db.get(User, user_id)
            if user is None:
                return True
            is_admin = user.role == "admin"
        finally:
            db.close()

        await sio.enter_room(sid, f"user:{user_id}")
        if is_admin:
            await sio.enter_room(sid, "admins")
    except (TokenError, ValueError, Exception):
        pass

    return True


@sio.event
async def disconnect(sid):
    pass


@sio.event
async def ping(sid, data=None):
    await sio.emit("pong", room=sid)


@sio.event
async def join_testrec(sid, data):
    """Join test recommendation rooms: global + session-specific."""
    await sio.enter_room(sid, "testrec_all")
    session_id = data.get("session_id") if isinstance(data, dict) else None
    if session_id:
        await sio.enter_room(sid, f"testrec:{session_id}")
