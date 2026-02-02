"""
Authentication Module - Google OAuth Implementation

Handles Google OAuth 2.0 authentication flow, session management,
and user authorization based on email whitelist.
"""

import os
import secrets
from typing import Optional
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeSerializer

from .session_store import session_store
from .user_store import user_store


# Initialize OAuth client
oauth = OAuth()

def configure_oauth():
    """Configure OAuth client with Google credentials."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("WARNING: OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.")
        return False

    oauth.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    return True


# Session serializer for signing session IDs
def get_serializer() -> URLSafeSerializer:
    """Get session serializer with secret key."""
    secret_key = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
    return URLSafeSerializer(secret_key)


def sign_session_id(session_id: str) -> str:
    """Sign a session ID to prevent tampering."""
    serializer = get_serializer()
    return serializer.dumps(session_id)


def verify_session_id(signed_session_id: str) -> Optional[str]:
    """Verify and extract session ID from signed value."""
    try:
        serializer = get_serializer()
        return serializer.loads(signed_session_id)
    except Exception:
        return None


async def handle_login(request: Request):
    """Handle OAuth login initiation."""
    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")

    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)


async def handle_callback(request: Request):
    """Handle OAuth callback from Google."""
    # Verify state parameter (CSRF protection)
    state = request.query_params.get("state")
    session_state = request.session.get("oauth_state")

    if not state or not session_state or state != session_state:
        return RedirectResponse("/login.html?error=invalid_state")

    # Clear state from session
    request.session.pop("oauth_state", None)

    try:
        # Exchange authorization code for tokens
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get("userinfo")
        if not user_info:
            return RedirectResponse("/login.html?error=no_userinfo")

        email = user_info.get("email")
        if not email:
            return RedirectResponse("/login.html?error=no_email")

        # Check user status via user_store
        status = user_store.request_access(email)

        if status == "approved":
            # Admin or previously approved user - create session immediately
            session_id = session_store.create_session(email)
            signed_session_id = sign_session_id(session_id)

            # Set session cookie
            response = RedirectResponse("/")
            response.set_cookie(
                key="session",
                value=signed_session_id,
                httponly=True,
                secure=os.getenv("APP_ENV") == "production",  # HTTPS only in production
                samesite="lax",
                max_age=60 * 60 * 24 * 7  # 7 days
            )

            print(f"Successful login: {email}")
            return response

        elif status == "denied":
            # Previously denied user
            print(f"Denied login attempt: {email}")
            return RedirectResponse("/login.html?error=unauthorized")

        elif status == "pending":
            # New user - create temporary session to track pending email, redirect to pending page
            session_id = session_store.create_session(email)
            signed_session_id = sign_session_id(session_id)

            response = RedirectResponse("/pending.html")
            response.set_cookie(
                key="session",
                value=signed_session_id,
                httponly=True,
                secure=os.getenv("APP_ENV") == "production",
                samesite="lax",
                max_age=60 * 60 * 24  # 1 day for pending sessions
            )

            print(f"Pending access request: {email}")
            return response

    except Exception as e:
        print(f"OAuth callback error: {e}")
        return RedirectResponse("/login.html?error=auth_failed")


async def handle_logout(request: Request):
    """Handle logout."""
    # Get session ID from cookie
    signed_session_id = request.cookies.get("session")

    if signed_session_id:
        session_id = verify_session_id(signed_session_id)
        if session_id:
            session_store.delete_session(session_id)

    # Clear session cookie
    response = RedirectResponse("/login.html")
    response.delete_cookie("session")

    return response


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency to get current authenticated user.
    Raises 401 if not authenticated.
    """
    # Check if OAuth is configured
    if not os.getenv("GOOGLE_CLIENT_ID"):
        # OAuth not configured, allow access (dev mode)
        return {"email": "dev@localhost", "dev_mode": True}

    signed_session_id = request.cookies.get("session")

    if not signed_session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify signature
    session_id = verify_session_id(signed_session_id)
    if not session_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Get session data
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    return {"email": session["email"], "session_id": session_id}


def is_authenticated(request: Request) -> bool:
    """Check if request has valid session (for HTML routes)."""
    # Check if OAuth is configured
    if not os.getenv("GOOGLE_CLIENT_ID"):
        # OAuth not configured, allow access (dev mode)
        return True

    signed_session_id = request.cookies.get("session")

    if not signed_session_id:
        return False

    session_id = verify_session_id(signed_session_id)
    if not session_id:
        return False

    session = session_store.get_session(session_id)
    return session is not None


def is_admin_user(request: Request) -> bool:
    """Check if current user is an admin."""
    if not os.getenv("GOOGLE_CLIENT_ID"):
        return True  # Dev mode - everyone is admin

    signed_session_id = request.cookies.get("session")
    if not signed_session_id:
        return False

    session_id = verify_session_id(signed_session_id)
    if not session_id:
        return False

    session = session_store.get_session(session_id)
    if not session:
        return False

    return user_store.is_admin(session["email"])


def get_pending_email(request: Request) -> Optional[str]:
    """Get the email address for a pending access request session."""
    signed_session_id = request.cookies.get("session")
    if not signed_session_id:
        return None

    session_id = verify_session_id(signed_session_id)
    if not session_id:
        return None

    session = session_store.get_session(session_id)
    if not session:
        return None

    return session["email"]


async def get_auth_status(request: Request) -> dict:
    """Get current authentication status (for frontend)."""
    if not os.getenv("GOOGLE_CLIENT_ID"):
        return {
            "authenticated": True,
            "email": "dev@localhost",
            "dev_mode": True,
            "is_admin": True
        }

    signed_session_id = request.cookies.get("session")

    if not signed_session_id:
        return {"authenticated": False}

    session_id = verify_session_id(signed_session_id)
    if not session_id:
        return {"authenticated": False}

    session = session_store.get_session(session_id)
    if not session:
        return {"authenticated": False}

    email = session["email"]
    is_admin = user_store.is_admin(email)
    is_approved = user_store.is_approved(email)

    return {
        "authenticated": is_approved,  # Only approved users are fully authenticated
        "email": email,
        "created_at": session["created_at"].isoformat(),
        "expires_at": session["expires_at"].isoformat(),
        "is_admin": is_admin
    }
