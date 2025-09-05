"""SAML SSO API routes for BOL-CD"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from typing import Dict, Any

from ..auth.saml import SAMLManager, SAML_AVAILABLE
from ..auth.manager import AuthManager

router = APIRouter(prefix="/api/v1/auth/saml", tags=["SAML SSO"])


@router.get("/metadata", response_class=Response)
async def saml_metadata():
    """Get Service Provider metadata XML"""
    if not SAML_AVAILABLE:
        raise HTTPException(status_code=501, detail="SAML not configured")
    
    saml_manager = SAMLManager()
    metadata_xml = saml_manager.get_metadata()
    
    return Response(
        content=metadata_xml,
        media_type="application/xml",
        headers={"Content-Disposition": "inline; filename=sp-metadata.xml"}
    )


@router.get("/sso")
async def saml_sso_init(request: Request):
    """Initialize SAML SSO login flow"""
    if not SAML_AVAILABLE:
        raise HTTPException(status_code=501, detail="SAML not configured")
    
    # Prepare request data for python3-saml
    request_data = {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.headers.get("host", "localhost"),
        "script_name": request.url.path,
        "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
        "get_data": dict(request.query_params),
        "post_data": {}
    }
    
    saml_manager = SAMLManager()
    result = saml_manager.init_sso(request_data)
    
    # Redirect to IdP
    return RedirectResponse(url=result["sso_url"])


@router.post("/acs")
async def saml_acs(request: Request):
    """SAML Assertion Consumer Service - process IdP response"""
    if not SAML_AVAILABLE:
        raise HTTPException(status_code=501, detail="SAML not configured")
    
    # Get form data
    form_data = await request.form()
    
    # Prepare request data for python3-saml
    request_data = {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.headers.get("host", "localhost"),
        "script_name": request.url.path,
        "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
        "get_data": dict(request.query_params),
        "post_data": dict(form_data)
    }
    
    saml_manager = SAMLManager()
    result = saml_manager.process_response(request_data)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "SAML authentication failed")
        )
    
    # Return tokens or redirect to app with tokens
    tokens = result.get("tokens")
    user = result.get("user")
    
    # In production, you'd set secure cookies or redirect with tokens
    # For now, return JSON response
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "role": user.role
        },
        "tokens": tokens
    }


@router.get("/slo")
async def saml_slo_init(request: Request, user_email: str):
    """Initialize SAML Single Logout"""
    if not SAML_AVAILABLE:
        raise HTTPException(status_code=501, detail="SAML not configured")
    
    saml_manager = SAMLManager()
    result = saml_manager.init_slo(user_email)
    
    # Redirect to IdP for logout
    return RedirectResponse(url=result["slo_url"])


@router.post("/sls")
async def saml_sls(request: Request):
    """SAML Single Logout Service - process IdP logout response"""
    if not SAML_AVAILABLE:
        raise HTTPException(status_code=501, detail="SAML not configured")
    
    # Process logout response
    # In production, clear session/cookies
    
    # Redirect to logout success page
    return RedirectResponse(url="/logout-success")
