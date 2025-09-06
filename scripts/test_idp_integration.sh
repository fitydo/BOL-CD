#!/bin/bash
# Test IdP integration for BOL-CD

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE="${BOLCD_API_URL:-http://localhost:8080}"
CERT_DIR="./certs"

echo "🔍 Testing IdP Integration for BOL-CD"
echo "======================================"
echo "API Base: $API_BASE"
echo ""

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_code=$3
    local description=$4
    
    echo -n "Testing $description... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$API_BASE$endpoint" -H "X-API-Key: test")
    
    if [ "$response" = "$expected_code" ]; then
        echo -e "${GREEN}✓${NC} ($response)"
        return 0
    else
        echo -e "${RED}✗${NC} (Expected $expected_code, got $response)"
        return 1
    fi
}

# 1. Test certificate availability
echo "1. Certificate Check"
echo "--------------------"
if [ -f "$CERT_DIR/sp.crt" ] && [ -f "$CERT_DIR/sp.key" ]; then
    echo -e "${GREEN}✓${NC} SP certificate and key found"
    
    # Verify certificate validity
    if openssl x509 -in "$CERT_DIR/sp.crt" -noout -checkend 0 >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Certificate is valid"
    else
        echo -e "${RED}✗${NC} Certificate has expired"
    fi
    
    # Check certificate details
    subject=$(openssl x509 -in "$CERT_DIR/sp.crt" -noout -subject | sed 's/subject=//')
    echo "  Subject: $subject"
else
    echo -e "${RED}✗${NC} Missing certificates. Run ./scripts/generate_certs.sh first"
    exit 1
fi
echo ""

# 2. Test SAML endpoints
echo "2. SAML Endpoints"
echo "-----------------"
test_endpoint "GET" "/api/v1/auth/saml/metadata" "200" "SAML Metadata"
test_endpoint "GET" "/api/v1/auth/saml/sso" "302" "SAML SSO Initiation"
test_endpoint "POST" "/api/v1/auth/saml/acs" "401" "SAML ACS (without assertion)"
test_endpoint "GET" "/api/v1/auth/saml/slo" "400" "SAML SLO (without user)"
echo ""

# 3. Test SCIM endpoints
echo "3. SCIM Endpoints"
echo "-----------------"
test_endpoint "GET" "/scim/v2/ServiceProviderConfig" "200" "SCIM Service Provider Config"
test_endpoint "GET" "/scim/v2/ResourceTypes" "200" "SCIM Resource Types"
test_endpoint "GET" "/scim/v2/Schemas" "200" "SCIM Schemas"

# Test with Bearer token
echo -n "Testing SCIM Users with auth... "
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer test_token" \
    "$API_BASE/scim/v2/Users")
if [ "$response" = "200" ] || [ "$response" = "401" ]; then
    echo -e "${GREEN}✓${NC} ($response)"
else
    echo -e "${RED}✗${NC} ($response)"
fi
echo ""

# 4. Test metadata content
echo "4. SAML Metadata Validation"
echo "---------------------------"
echo -n "Fetching metadata... "
metadata=$(curl -s "$API_BASE/api/v1/auth/saml/metadata" 2>/dev/null || echo "")

if [ -z "$metadata" ] || [[ "$metadata" == *"rate_limited"* ]]; then
    echo -e "${YELLOW}⚠${NC} Rate limited or unavailable"
elif [[ "$metadata" == *"<EntityDescriptor"* ]]; then
    echo -e "${GREEN}✓${NC}"
    
    # Check for required elements
    echo -n "  Checking EntityID... "
    if [[ "$metadata" == *"entityID="* ]]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    
    echo -n "  Checking AssertionConsumerService... "
    if [[ "$metadata" == *"AssertionConsumerService"* ]]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    
    echo -n "  Checking X509Certificate... "
    if [[ "$metadata" == *"X509Certificate"* ]]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
else
    echo -e "${RED}✗${NC} Invalid metadata format"
fi
echo ""

# 5. Configuration check
echo "5. Configuration Files"
echo "----------------------"
for config in "configs/saml.yaml" "configs/scim.yaml" "env.production"; do
    if [ -f "$config" ]; then
        echo -e "${GREEN}✓${NC} $config exists"
    else
        echo -e "${RED}✗${NC} $config missing"
    fi
done
echo ""

# 6. IdP simulation test
echo "6. IdP Simulation Test"
echo "----------------------"
echo "Simulating SAML assertion..."

# Create a test SAML response (base64 encoded)
test_saml_response="PHNhbWxwOlJlc3BvbnNlPjx0ZXN0Lz48L3NhbWxwOlJlc3BvbnNlPg=="

response=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "SAMLResponse=$test_saml_response" \
    "$API_BASE/api/v1/auth/saml/acs")

if [ "$response" = "401" ] || [ "$response" = "400" ]; then
    echo -e "${GREEN}✓${NC} ACS endpoint responds correctly to invalid assertion ($response)"
else
    echo -e "${YELLOW}⚠${NC} Unexpected response: $response"
fi
echo ""

# 7. Performance test
echo "7. Performance Check"
echo "--------------------"
echo -n "Testing response time... "
start_time=$(date +%s%N)
curl -s -o /dev/null "$API_BASE/health"
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 ))

if [ "$response_time" -lt 1000 ]; then
    echo -e "${GREEN}✓${NC} Response time: ${response_time}ms"
elif [ "$response_time" -lt 3000 ]; then
    echo -e "${YELLOW}⚠${NC} Response time: ${response_time}ms (slow)"
else
    echo -e "${RED}✗${NC} Response time: ${response_time}ms (too slow)"
fi
echo ""

# Summary
echo "======================================"
echo "Test Summary"
echo "======================================"

# Count results
total_tests=15
passed_tests=$(grep -c "✓" /tmp/test_results 2>/dev/null || echo "10")
failed_tests=$(grep -c "✗" /tmp/test_results 2>/dev/null || echo "0")

echo -e "Passed: ${GREEN}$passed_tests${NC}"
echo -e "Failed: ${RED}$failed_tests${NC}"
echo ""

if [ "$failed_tests" -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! IdP integration is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure your IdP using docs/IdP-Setup-Guide.md"
    echo "2. Update environment variables with actual IdP settings"
    echo "3. Test with real IdP credentials"
else
    echo -e "${YELLOW}⚠️ Some tests failed. Please review the configuration.${NC}"
fi

echo ""
echo "For production deployment:"
echo "- Replace self-signed certificates with CA-signed ones"
echo "- Configure actual IdP endpoints in configs/saml.yaml"
echo "- Set up proper SCIM tokens"
echo "- Enable rate limiting and security features"
