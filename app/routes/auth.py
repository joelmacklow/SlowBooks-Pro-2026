from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    AuthSessionResponse,
    BootstrapAdminRequest,
    CurrentSessionResponse,
    LoginRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
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
    update_user_account,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/bootstrap-admin", response_model=AuthSessionResponse)
def bootstrap_admin(data: BootstrapAdminRequest, db: Session = Depends(get_db)):
    token, user = bootstrap_admin_user(db, data.email, data.password, data.full_name)
    return AuthSessionResponse(token=token, user=user)


@router.post("/login", response_model=AuthSessionResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    token, user = login_user(db, data.email, data.password)
    return AuthSessionResponse(token=token, user=user)


@router.post("/logout")
def logout(db: Session = Depends(get_db), auth=Depends(require_permissions())):
    revoke_session(db, auth)
    return {"status": "logged_out"}


@router.get("/me", response_model=CurrentSessionResponse)
def me(db: Session = Depends(get_db), auth=Depends(get_optional_auth_context)):
    if not auth:
        return CurrentSessionResponse(authenticated=False, user=None)
    return CurrentSessionResponse(authenticated=True, user=build_user_response(auth.user, auth.membership))


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
        is_active=data.is_active,
        membership_active=data.membership_active,
    )
