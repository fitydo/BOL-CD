"""Authentication routes for the API."""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..auth import AuthManager, User, UserCreate, UserLogin, Token
from ..auth.models import GoogleAuthRequest, UserUpdate, PasswordChange

# Initialize router and auth manager
router = APIRouter(prefix="/api/auth", tags=["authentication"])
auth_manager = AuthManager()
security = HTTPBearer(auto_error=False)


# Protected route dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    db = auth_manager.SessionLocal()
    try:
        user = auth_manager.get_current_user(credentials.credentials, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return user
    finally:
        db.close()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user."""
    db = auth_manager.SessionLocal()
    try:
        user = auth_manager.register_user(user_data, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        return auth_manager.create_tokens(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    finally:
        db.close()


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login with email and password."""
    db = auth_manager.SessionLocal()
    try:
        user = auth_manager.authenticate_user(
            credentials.email, 
            credentials.password, 
            db
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        return auth_manager.create_tokens(user)
    finally:
        db.close()


@router.post("/google", response_model=Token)
async def google_auth(auth_request: GoogleAuthRequest):
    """Authenticate with Google OAuth."""
    db = auth_manager.SessionLocal()
    try:
        user = auth_manager.authenticate_google(auth_request.id_token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google authentication failed"
            )
        return auth_manager.create_tokens(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    finally:
        db.close()


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=User)
async def update_me(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user profile."""
    db = auth_manager.SessionLocal()
    try:
        updated_user = auth_manager.update_user(
            current_user.id,
            updates.dict(exclude_unset=True),
            db
        )
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return updated_user
    finally:
        db.close()


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user)
):
    """Change user password."""
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    db = auth_manager.SessionLocal()
    try:
        success = auth_manager.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password,
            db
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password"
            )
    finally:
        db.close()


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(current_user: User = Depends(get_current_user)):
    """Delete current user account."""
    db = auth_manager.SessionLocal()
    try:
        success = auth_manager.delete_user(current_user.id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    finally:
        db.close()
