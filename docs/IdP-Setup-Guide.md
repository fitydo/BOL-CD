# Identity Provider (IdP) Setup Guide for BOL-CD

This guide walks you through configuring popular Identity Providers for SAML SSO and SCIM provisioning with BOL-CD.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Okta Setup](#okta-setup)
- [Azure AD Setup](#azure-ad-setup)
- [Google Workspace Setup](#google-workspace-setup)
- [Generic SAML IdP Setup](#generic-saml-idp-setup)
- [Testing & Troubleshooting](#testing--troubleshooting)

## Prerequisites

1. **Generate SP Certificates**
   ```bash
   ./scripts/generate_certs.sh
   ```

2. **Get SP Metadata URL**
   ```
   https://your-bolcd-domain.com/api/v1/auth/saml/metadata
   ```

3. **Have Admin Access** to your Identity Provider

## Okta Setup

### 1. Create SAML Application

1. Log in to Okta Admin Console
2. Navigate to **Applications** → **Applications**
3. Click **Create App Integration**
4. Select **SAML 2.0** and click **Next**

### 2. Configure SAML Settings

**General Settings:**
- App name: `BOL-CD`
- App logo: Upload BOL-CD logo (optional)

**SAML Settings:**
- Single Sign On URL: `https://your-domain.com/api/v1/auth/saml/acs`
- Use this for Recipient URL and Destination URL: ✓
- Audience URI (SP Entity ID): `https://your-domain.com`
- Default RelayState: (leave blank)
- Name ID format: `EmailAddress`
- Application username: `Email`

**Attribute Statements:**
| Name | Name Format | Value |
|------|-------------|-------|
| email | Basic | user.email |
| firstName | Basic | user.firstName |
| lastName | Basic | user.lastName |
| displayName | Basic | user.displayName |
| groups | Basic | appuser.groups |

**Group Attribute Statements:**
- Name: `groups`
- Name format: `Basic`
- Filter: `Matches regex: .*`

### 3. Configure SCIM Provisioning

1. Navigate to **Provisioning** tab
2. Click **Configure API Integration**
3. Enable **Enable API integration**
4. Enter:
   - Base URL: `https://your-domain.com/scim/v2`
   - API Token: Generate and copy from BOL-CD
5. Click **Test API Credentials**

**Provisioning Settings:**
- Create Users: ✓
- Update User Attributes: ✓
- Deactivate Users: ✓

### 4. Download IdP Certificate

1. Go to **Sign On** tab
2. Under **SAML Signing Certificates**, click **Actions** → **Download Certificate**
3. Save as `okta_idp.crt`

### 5. Update BOL-CD Configuration

```bash
# Copy certificate
cp okta_idp.crt ./certs/

# Update environment variables
SAML_IDP_TYPE=okta
SAML_OKTA_ENTITY_ID=http://www.okta.com/YOUR_ORG_ID
SAML_OKTA_SSO_URL=https://YOUR_DOMAIN.okta.com/app/YOUR_APP_ID/sso/saml
SAML_OKTA_CERT_FILE=./certs/okta_idp.crt
SCIM_TOKEN_OKTA=YOUR_GENERATED_TOKEN
```

## Azure AD Setup

### 1. Create Enterprise Application

1. Sign in to Azure Portal
2. Navigate to **Azure Active Directory** → **Enterprise applications**
3. Click **New application** → **Create your own application**
4. Name: `BOL-CD`
5. Select **Integrate any other application** and click **Create**

### 2. Configure SAML SSO

1. Go to **Single sign-on** → Select **SAML**
2. Edit **Basic SAML Configuration**:
   - Identifier (Entity ID): `https://your-domain.com`
   - Reply URL: `https://your-domain.com/api/v1/auth/saml/acs`
   - Sign on URL: `https://your-domain.com/login`
   - Relay State: (optional)
   - Logout URL: `https://your-domain.com/api/v1/auth/saml/sls`

3. Edit **User Attributes & Claims**:
   - Unique User Identifier: `user.mail`
   - Add claims:
     - `email` → `user.mail`
     - `name` → `user.displayname`
     - `groups` → `user.groups`

### 3. Configure SCIM Provisioning

1. Go to **Provisioning** → **Get started**
2. Provisioning Mode: **Automatic**
3. Admin Credentials:
   - Tenant URL: `https://your-domain.com/scim/v2`
   - Secret Token: Generate from BOL-CD
4. Click **Test Connection**

**Mappings:**
- Provision Azure AD Users: ✓
- Provision Azure AD Groups: ✓

### 4. Download Certificate

1. In **SAML Signing Certificate** section
2. Download **Certificate (Base64)**
3. Save as `azure_idp.crt`

### 5. Update BOL-CD Configuration

```bash
# Copy certificate
cp azure_idp.crt ./certs/

# Update environment variables
SAML_IDP_TYPE=azure
SAML_AZURE_TENANT_ID=YOUR_TENANT_ID
SAML_AZURE_APP_ID=YOUR_APP_ID
SAML_AZURE_CERT_FILE=./certs/azure_idp.crt
SCIM_TOKEN_AZURE=YOUR_GENERATED_TOKEN
```

## Google Workspace Setup

### 1. Create SAML App

1. Sign in to Google Admin Console
2. Go to **Apps** → **Web and mobile apps**
3. Click **Add app** → **Add custom SAML app**

### 2. App Details

- App name: `BOL-CD`
- App description: `Security Operations Alert Reduction Platform`
- Upload logo (optional)

### 3. Google IdP Information

1. Download **Certificate**
2. Copy:
   - SSO URL
   - Entity ID
3. Save certificate as `google_idp.crt`

### 4. Service Provider Details

- ACS URL: `https://your-domain.com/api/v1/auth/saml/acs`
- Entity ID: `https://your-domain.com`
- Start URL: `https://your-domain.com/login`
- Signed Response: ✓
- Name ID Format: `EMAIL`
- Name ID: `Basic Information > Primary email`

### 5. Attribute Mapping

| Google Directory | App Attribute |
|------------------|---------------|
| Basic Information > Primary email | email |
| Basic Information > First name | firstName |
| Basic Information > Last name | lastName |
| Basic Information > Full name | displayName |

### 6. Update BOL-CD Configuration

```bash
# Copy certificate
cp google_idp.crt ./certs/

# Update environment variables
SAML_IDP_TYPE=google
SAML_GOOGLE_DOMAIN=your-domain.com
SAML_GOOGLE_IDP_ID=YOUR_IDP_ID
SAML_GOOGLE_CERT_FILE=./certs/google_idp.crt
```

## Generic SAML IdP Setup

For other SAML 2.0 compatible IdPs (PingIdentity, OneLogin, Auth0, etc.):

### Required Information from IdP

1. **Entity ID** (Issuer)
2. **SSO URL** (Sign-in URL)
3. **SLO URL** (Sign-out URL) - optional
4. **X.509 Certificate**
5. **Attribute mappings**

### SP Information to Provide to IdP

- **Entity ID**: `https://your-domain.com`
- **ACS URL**: `https://your-domain.com/api/v1/auth/saml/acs`
- **SLS URL**: `https://your-domain.com/api/v1/auth/saml/sls`
- **SP Certificate**: Generated from `./scripts/generate_certs.sh`
- **NameID Format**: `emailAddress` (recommended)

### Configuration

```yaml
# In configs/saml.yaml
idps:
  generic:
    enabled: true
    entity_id: "https://idp.example.com"
    sso_service:
      url: "https://idp.example.com/sso/saml"
    x509cert: |
      -----BEGIN CERTIFICATE-----
      [Your IdP Certificate]
      -----END CERTIFICATE-----
```

## Testing & Troubleshooting

### 1. Test SAML Metadata

```bash
curl https://your-domain.com/api/v1/auth/saml/metadata
```

### 2. Test SSO Flow

1. Navigate to: `https://your-domain.com/api/v1/auth/saml/sso`
2. Should redirect to IdP login
3. After authentication, redirects back to BOL-CD

### 3. Test SCIM Provisioning

```bash
# Test connection (replace with your token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/scim/v2/ServiceProviderConfig
```

### 4. Common Issues

**"Invalid SAML Response"**
- Check certificate is correctly configured
- Verify Entity ID matches
- Ensure clock sync between IdP and SP

**"User not provisioned"**
- Check SCIM token is valid
- Verify attribute mappings
- Check user is assigned to app in IdP

**"Access Denied after SSO"**
- Verify group mappings in `configs/saml.yaml`
- Check user has required groups in IdP
- Review role_mapping configuration

### 5. Debug Mode

Enable debug logging for troubleshooting:

```bash
BOLCD_DEBUG=1
BOLCD_LOG_LEVEL=debug
SAML_DEBUG=true
```

### 6. Logs to Check

```bash
# SAML authentication logs
tail -f /var/log/bolcd/saml.log

# SCIM provisioning logs
tail -f /var/log/bolcd/scim.log

# General application logs
tail -f /var/log/bolcd/app.log
```

## Security Best Practices

1. **Use HTTPS** for all endpoints
2. **Rotate certificates** annually
3. **Use strong tokens** for SCIM (min 32 characters)
4. **Enable signature verification** for SAML assertions
5. **Implement IP whitelisting** for SCIM endpoints
6. **Regular audit** of provisioned users
7. **Monitor failed** authentication attempts
8. **Use separate** certificates for different environments

## Support

For additional help:
- Documentation: https://docs.bolcd.example.com
- Support: support@bolcd.example.com
- Community: https://community.bolcd.example.com
