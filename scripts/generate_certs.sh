#!/bin/bash
# Generate certificates for SAML/TLS

set -e

CERT_DIR="./certs"
DOMAIN="${BOLCD_DOMAIN:-bolcd.local}"
DAYS="${CERT_DAYS:-3650}"

echo "🔐 Generating certificates for BOL-CD..."
echo "   Domain: $DOMAIN"
echo "   Valid for: $DAYS days"

# Create certificate directory
mkdir -p "$CERT_DIR"
chmod 700 "$CERT_DIR"

# Generate private key
echo "1. Generating private key..."
openssl genrsa -out "$CERT_DIR/sp.key" 2048

# Generate certificate signing request
echo "2. Creating certificate signing request..."
cat > "$CERT_DIR/csr.conf" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[dn]
C=JP
ST=Tokyo
L=Tokyo
O=BOL-CD
OU=Security Operations
CN=$DOMAIN
emailAddress=admin@$DOMAIN
EOF

openssl req -new -key "$CERT_DIR/sp.key" -out "$CERT_DIR/sp.csr" -config "$CERT_DIR/csr.conf"

# Generate self-signed certificate for development
echo "3. Generating self-signed certificate..."
openssl x509 -req -days "$DAYS" -in "$CERT_DIR/sp.csr" -signkey "$CERT_DIR/sp.key" -out "$CERT_DIR/sp.crt"

# Generate DH parameters for enhanced security
echo "4. Generating DH parameters (this may take a while)..."
openssl dhparam -out "$CERT_DIR/dhparam.pem" 2048 2>/dev/null || true

# Create SAML metadata signing certificate
echo "5. Creating SAML metadata signing certificate..."
openssl req -x509 -new -nodes -key "$CERT_DIR/sp.key" \
    -sha256 -days "$DAYS" -out "$CERT_DIR/saml_signing.crt" \
    -subj "/C=JP/ST=Tokyo/O=BOL-CD/CN=SAML Signing Certificate"

# Set proper permissions
chmod 600 "$CERT_DIR"/*.key
chmod 644 "$CERT_DIR"/*.crt
chmod 644 "$CERT_DIR"/*.pem 2>/dev/null || true

# Create certificate bundle for IdP
echo "6. Creating certificate bundle..."
cat "$CERT_DIR/sp.crt" "$CERT_DIR/saml_signing.crt" > "$CERT_DIR/bundle.crt"

# Display certificate info
echo ""
echo "✅ Certificates generated successfully!"
echo ""
echo "Certificate details:"
openssl x509 -in "$CERT_DIR/sp.crt" -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After)"

echo ""
echo "Files created:"
ls -la "$CERT_DIR"/*.{key,crt,pem} 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes)"}'

echo ""
echo "⚠️  For production, replace these with certificates from a trusted CA!"
echo ""
echo "Next steps:"
echo "1. Copy sp.crt to your IdP as the SP certificate"
echo "2. Configure your IdP's certificate in configs/saml.yaml"
echo "3. Update SAML_CERT_FILE and SAML_KEY_FILE in your .env file"
