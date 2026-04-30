import hmac
import ipaddress

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import BOOTSTRAP_ADMIN_TOKEN, SESSION_COOKIE_NAME, SESSION_COOKIE_SAMESITE, SESSION_COOKIE_SECURE
from app.database import get_db
from app.schemas.auth import (
    AuthMetaResponse,
    AuthSessionResponse,
    BootstrapAdminRequest,
    CurrentSessionResponse,
    LoginRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.company_service import list_company_scope_options
from app.services.auth import (
    bootstrap_admin_user,
    build_user_response,
    create_user_account,
    get_auth_context,
    get_optional_auth_context,
    list_user_accounts,
    login_user,
    require_permissions,
    revoke_session,
    supported_permission_definitions,
    supported_role_definitions,
    update_user_account,
    users_exist,
)
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    candidate = host.strip().lower()
    if candidate == "localhost":
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def _enforce_bootstrap_request_trust(request: Request | None, bootstrap_token: str | None = None) -> None:
    if request is None:
        return
    client_host = request.client.host if request.client else None
    if _is_loopback_host(client_host):
        return
    if BOOTSTRAP_ADMIN_TOKEN and hmac.compare_digest((bootstrap_token or "").strip(), BOOTSTRAP_ADMIN_TOKEN):
        return
    raise HTTPException(
        status_code=403,
        detail="Initial admin bootstrap is only allowed from loopback or with a valid bootstrap token",
    )


def _set_session_cookie(response: Response | None, token: str) -> None:
    if response is None:
        return
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


def _clear_session_cookie(response: Response | None) -> None:
    if response is None:
        return
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
    )


@router.post("/bootstrap-admin", response_model=AuthSessionResponse)
def bootstrap_admin(
    data: BootstrapAdminRequest,
    response: Response = None,
    db: Session = Depends(get_db),
    request: Request = None,
    x_bootstrap_token: str | None = Header(default=None, alias="X-Bootstrap-Token"),
):
    enforce_rate_limit(
        request,
        scope="auth:bootstrap-admin",
        limit=5,
        window_seconds=300,
        detail="Too many bootstrap attempts. Please wait and try again.",
    )
    _enforce_bootstrap_request_trust(request, x_bootstrap_token)
    token, user = bootstrap_admin_user(db, data.email, data.password, data.full_name)
    _set_session_cookie(response, token)
    return AuthSessionResponse(token=token, user=user)


@router.post("/login", response_model=AuthSessionResponse)
def login(
    data: LoginRequest,
    response: Response = None,
    db: Session = Depends(get_db),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="auth:login",
        limit=10,
        window_seconds=300,
        detail="Too many login attempts. Please wait and try again.",
    )
    token, user = login_user(db, data.email, data.password)
    _set_session_cookie(response, token)
    return AuthSessionResponse(token=token, user=user)


@router.post("/logout")
def logout(response: Response = None, db: Session = Depends(get_db), auth=Depends(require_permissions())):
    revoke_session(db, auth)
    _clear_session_cookie(response)
    return {"status": "logged_out"}


@router.get("/me", response_model=CurrentSessionResponse)
def me(db: Session = Depends(get_db), auth=Depends(get_optional_auth_context)):
    if not auth:
        return CurrentSessionResponse(authenticated=False, bootstrap_required=not users_exist(db), user=None)
    return CurrentSessionResponse(
        authenticated=True,
        bootstrap_required=False,
        user=build_user_response(auth.user, auth.membership),
    )


@router.get("/meta", response_model=AuthMetaResponse)
def auth_meta(db: Session = Depends(get_db), auth=Depends(require_permissions("users.manage"))):
    return AuthMetaResponse(
        roles=supported_role_definitions(),
        permissions=supported_permission_definitions(),
        company_scopes=list_company_scope_options(db),
    )


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), auth=Depends(require_permissions("users.manage"))):
    return list_user_accounts(db)


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(data: UserCreateRequest, db: Session = Depends(get_db), auth=Depends(require_permissions("users.manage"))):
    return create_user_account(
        db,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role_key=data.role_key,
        allow_permissions=data.allow_permissions,
        deny_permissions=data.deny_permissions,
        company_scopes=data.company_scopes,
        is_active=data.is_active,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdateRequest, db: Session = Depends(get_db), auth=Depends(require_permissions("users.manage"))):
    return update_user_account(
        db,
        user_id,
        full_name=data.full_name,
        password=data.password,
        role_key=data.role_key,
        allow_permissions=data.allow_permissions,
        deny_permissions=data.deny_permissions,
        company_scopes=data.company_scopes,
        is_active=data.is_active,
        membership_active=data.membership_active,
    )
