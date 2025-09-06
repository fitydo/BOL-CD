"""SAML 2.0 SSO Integration for BOL-CD

This module provides SAML authentication support for enterprise SSO.
Supports popular IdPs like Okta, Azure AD, Google Workspace, OneLogin.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional

try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.utils import OneLogin_Saml2_Utils  # noqa: F401
    SAML_AVAILABLE = True
except ImportError:
    SAML_AVAILABLE = False

from .manager import AuthManager


class SAMLConfig:
    """SAML configuration for different IdPs"""
    
    @staticmethod
    def get_config(idp_type: str = "generic") -> Dict[str, Any]:
        """Get SAML settings for specific IdP"""
        base_url = os.getenv("BOLCD_BASE_URL", "http://localhost:8080")
        
        # Common settings
        settings = {
            "sp": {
                "entityId": f"{base_url}/api/v1/auth/saml/metadata",
                "assertionConsumerService": {
                    "url": f"{base_url}/api/v1/auth/saml/acs",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": f"{base_url}/api/v1/auth/saml/sls",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": os.getenv("BOLCD_SAML_SP_CERT", ""),
                "privateKey": os.getenv("BOLCD_SAML_SP_KEY", "")
            },
            "idp": {
                "entityId": os.getenv("BOLCD_SAML_IDP_ENTITY_ID", ""),
                "singleSignOnService": {
                    "url": os.getenv("BOLCD_SAML_IDP_SSO_URL", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": os.getenv("BOLCD_SAML_IDP_SLO_URL", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": os.getenv("BOLCD_SAML_IDP_CERT", "")
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": True,
                "logoutRequestSigned": True,
                "logoutResponseSigned": True,
                "signMetadata": False,
                "wantMessagesSigned": True,
                "wantAssertionsSigned": True,
                "wantAssertionsEncrypted": False,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "wantAttributeStatement": True,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
            }
        }
        
        # IdP-specific overrides
        if idp_type == "okta":
            settings["idp"]["entityId"] = os.getenv("BOLCD_OKTA_DOMAIN", "") + "/saml2/default"
            settings["idp"]["singleSignOnService"]["url"] = os.getenv("BOLCD_OKTA_DOMAIN", "") + "/app/bolcd/saml/sso"
        elif idp_type == "azure":
            tenant_id = os.getenv("BOLCD_AZURE_TENANT_ID", "")
            settings["idp"]["entityId"] = f"https://sts.windows.net/{tenant_id}/"
            settings["idp"]["singleSignOnService"]["url"] = f"https://login.microsoftonline.com/{tenant_id}/saml2"
        elif idp_type == "google":
            settings["idp"]["entityId"] = "https://accounts.google.com"
            settings["idp"]["singleSignOnService"]["url"] = "https://accounts.google.com/ServiceLogin"
            
        return settings


class SAMLManager:
    """Manages SAML authentication flow"""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self.auth_manager = auth_manager or AuthManager()
        self.idp_type = os.getenv("BOLCD_SAML_IDP_TYPE", "generic")
        
    def init_sso(self, request_data: Dict[str, Any]) -> Dict[str, str]:
        """Initialize SSO login flow"""
        if not SAML_AVAILABLE:
            raise ValueError("SAML libraries not installed. Run: pip install python3-saml")
            
        settings = SAMLConfig.get_config(self.idp_type)
        auth = OneLogin_Saml2_Auth(request_data, settings)
        
        # Generate SSO URL
        sso_url = auth.login()
        
        return {
            "sso_url": sso_url,
            "saml_request": auth.get_last_request_id()
        }
        
    def process_response(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process SAML response from IdP"""
        if not SAML_AVAILABLE:
            raise ValueError("SAML libraries not installed")
            
        settings = SAMLConfig.get_config(self.idp_type)
        auth = OneLogin_Saml2_Auth(request_data, settings)
        
        # Process the SAML response
        auth.process_response()
        
        errors = auth.get_errors()
        if errors:
            return {
                "success": False,
                "errors": errors,
                "last_error_reason": auth.get_last_error_reason()
            }
            
        if not auth.is_authenticated():
            return {
                "success": False,
                "error": "Authentication failed"
            }
            
        # Get user attributes from SAML response
        attributes = auth.get_attributes()
        nameid = auth.get_nameid()
        session_index = auth.get_session_index()
        
        # Map SAML attributes to user model
        email = nameid or attributes.get("email", [None])[0]
        if not email:
            return {
                "success": False,
                "error": "No email found in SAML response"
            }
            
        # Create or update user via SSO pathway
        full_name = attributes.get("displayName", [email])[0]
        db = self.auth_manager.get_db()
        try:
            user = self.auth_manager.create_or_update_sso_user(
                email=email,
                full_name=full_name,
                provider=self.idp_type,
                provider_id=None,
                db=db,
            )
        finally:
            db.close()
        tokens = self.auth_manager.create_tokens(user)
        
        return {
            "success": True,
            "user": user,
            "tokens": tokens,
            "session_index": session_index,
            "attributes": attributes
        }
        
    def init_slo(self, user_email: str, session_index: Optional[str] = None) -> Dict[str, str]:
        """Initialize Single Logout"""
        if not SAML_AVAILABLE:
            raise ValueError("SAML libraries not installed")
            
        settings = SAMLConfig.get_config(self.idp_type)
        
        # Create logout request
        request_data = {
            "https": "on",
            "http_host": os.getenv("BOLCD_BASE_URL", "localhost:8080").replace("http://", "").replace("https://", ""),
            "script_name": "/api/v1/auth/saml/sls"
        }
        
        auth = OneLogin_Saml2_Auth(request_data, settings)
        
        # Generate SLO URL
        slo_url = auth.logout(
            name_id=user_email,
            session_index=session_index,
            return_to=f"{os.getenv('BOLCD_BASE_URL', 'http://localhost:8080')}/logout"
        )
        
        return {
            "slo_url": slo_url,
            "saml_request": auth.get_last_request_id()
        }
        
    def get_metadata(self) -> str:
        """Generate SP metadata XML"""
        settings = SAMLConfig.get_config(self.idp_type)
        sp_settings = settings["sp"]
        
        # Generate metadata XML
        metadata = f"""<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
                  entityID="{sp_settings['entityId']}">
    <SPSSODescriptor AuthnRequestsSigned="true" 
                     WantAssertionsSigned="true"
                     protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <KeyDescriptor use="signing">
            <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
                <X509Data>
                    <X509Certificate>{sp_settings.get('x509cert', '')}</X509Certificate>
                </X509Data>
            </KeyInfo>
        </KeyDescriptor>
        <SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                            Location="{sp_settings['singleLogoutService']['url']}"/>
        <NameIDFormat>{sp_settings['NameIDFormat']}</NameIDFormat>
        <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                 Location="{sp_settings['assertionConsumerService']['url']}"
                                 index="1"/>
    </SPSSODescriptor>
    <Organization>
        <OrganizationName xml:lang="en">BOL-CD</OrganizationName>
        <OrganizationDisplayName xml:lang="en">BOL-CD Alert Reduction</OrganizationDisplayName>
        <OrganizationURL xml:lang="en">{os.getenv('BOLCD_BASE_URL', 'http://localhost:8080')}</OrganizationURL>
    </Organization>
</EntityDescriptor>"""
        
        return metadata
