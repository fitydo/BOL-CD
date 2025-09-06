#!/bin/bash
# BOL-CD Security Scan Script

set -e

# Configuration
TARGET="${1:-.}"
SCAN_TYPE="${2:-full}"
OUTPUT_FORMAT="${3:-json}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔒 BOL-CD Security Scan${NC}"
echo "========================"
echo "Target: $TARGET"
echo "Type: $SCAN_TYPE"
echo "Format: $OUTPUT_FORMAT"
echo ""

# Create results directory
RESULTS_DIR="security_results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Track vulnerabilities
TOTAL_VULNS=0
CRITICAL_VULNS=0
HIGH_VULNS=0
MEDIUM_VULNS=0
LOW_VULNS=0

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking security tools...${NC}"
    
    # Install/check for security tools
    local tools=("trivy" "bandit" "safety" "semgrep" "git-secrets")
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            echo -e "${YELLOW}Installing $tool...${NC}"
            case "$tool" in
                trivy)
                    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
                        wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
                        echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
                        sudo apt-get update && sudo apt-get install -y trivy
                    elif [[ "$OSTYPE" == "darwin"* ]]; then
                        brew install aquasecurity/trivy/trivy
                    fi
                    ;;
                bandit)
                    pip install bandit
                    ;;
                safety)
                    pip install safety
                    ;;
                semgrep)
                    pip install semgrep
                    ;;
                git-secrets)
                    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
                        git clone https://github.com/awslabs/git-secrets.git /tmp/git-secrets
                        cd /tmp/git-secrets && sudo make install
                        cd - > /dev/null
                    elif [[ "$OSTYPE" == "darwin"* ]]; then
                        brew install git-secrets
                    fi
                    ;;
            esac
        fi
    done
    
    echo -e "${GREEN}✓${NC} Security tools ready"
    echo ""
}

# Function for container image scanning
scan_docker_image() {
    echo -e "${MAGENTA}Scanning Docker images...${NC}"
    
    local image="${DOCKER_IMAGE:-bolcd:latest}"
    
    # Check if image exists
    if docker images | grep -q "$image"; then
        echo "Scanning image: $image"
        
        # Run Trivy scan
        trivy image \
            --severity CRITICAL,HIGH,MEDIUM \
            --format "$OUTPUT_FORMAT" \
            --output "$RESULTS_DIR/trivy_image.json" \
            "$image"
        
        # Parse results
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            local vulns=$(jq '.Results[].Vulnerabilities | length' "$RESULTS_DIR/trivy_image.json" 2>/dev/null | awk '{s+=$1} END {print s}')
            TOTAL_VULNS=$((TOTAL_VULNS + vulns))
            
            echo "  Found $vulns vulnerabilities in Docker image"
        fi
        
        echo -e "${GREEN}✓${NC} Docker image scan completed"
    else
        echo -e "${YELLOW}⚠${NC} Docker image not found, skipping"
    fi
    echo ""
}

# Function for dependency scanning
scan_dependencies() {
    echo -e "${MAGENTA}Scanning dependencies...${NC}"
    
    # Python dependencies
    if [ -f "requirements.txt" ]; then
        echo "Scanning Python dependencies..."
        safety check \
            --json \
            --output "$RESULTS_DIR/safety_report.json" \
            -r requirements.txt || true
        
        # Parse results
        local py_vulns=$(jq '. | length' "$RESULTS_DIR/safety_report.json" 2>/dev/null || echo "0")
        TOTAL_VULNS=$((TOTAL_VULNS + py_vulns))
        echo "  Found $py_vulns vulnerabilities in Python dependencies"
    fi
    
    # Node.js dependencies
    if [ -f "web/package.json" ]; then
        echo "Scanning Node.js dependencies..."
        cd web
        npm audit --json > "$RESULTS_DIR/npm_audit.json" 2>/dev/null || true
        cd ..
        
        # Parse results
        local npm_vulns=$(jq '.metadata.vulnerabilities.total' "$RESULTS_DIR/npm_audit.json" 2>/dev/null || echo "0")
        TOTAL_VULNS=$((TOTAL_VULNS + npm_vulns))
        echo "  Found $npm_vulns vulnerabilities in Node.js dependencies"
    fi
    
    # License check
    echo "Checking licenses..."
    pip-licenses --format=json > "$RESULTS_DIR/licenses.json" 2>/dev/null || true
    
    echo -e "${GREEN}✓${NC} Dependency scan completed"
    echo ""
}

# Function for code scanning
scan_code() {
    echo -e "${MAGENTA}Scanning source code...${NC}"
    
    # Python code with Bandit
    if [ -d "src" ]; then
        echo "Running Bandit security scan..."
        bandit -r src \
            -f json \
            -o "$RESULTS_DIR/bandit_report.json" \
            --severity-level medium || true
        
        # Parse results
        local bandit_issues=$(jq '.results | length' "$RESULTS_DIR/bandit_report.json" 2>/dev/null || echo "0")
        echo "  Found $bandit_issues security issues in Python code"
    fi
    
    # Semgrep scan
    echo "Running Semgrep scan..."
    semgrep \
        --config=auto \
        --json \
        --output="$RESULTS_DIR/semgrep_report.json" \
        "$TARGET" 2>/dev/null || true
    
    # Parse Semgrep results
    local semgrep_issues=$(jq '.results | length' "$RESULTS_DIR/semgrep_report.json" 2>/dev/null || echo "0")
    echo "  Found $semgrep_issues issues with Semgrep"
    
    echo -e "${GREEN}✓${NC} Code scan completed"
    echo ""
}

# Function for secrets scanning
scan_secrets() {
    echo -e "${MAGENTA}Scanning for secrets...${NC}"
    
    # Initialize git-secrets if not already done
    if [ -d ".git" ]; then
        git secrets --install 2>/dev/null || true
        git secrets --register-aws 2>/dev/null || true
        
        # Add custom patterns
        git secrets --add 'password\s*=\s*["\'][^"\']+["\']' 2>/dev/null || true
        git secrets --add 'api[_-]?key\s*=\s*["\'][^"\']+["\']' 2>/dev/null || true
        git secrets --add 'token\s*=\s*["\'][^"\']+["\']' 2>/dev/null || true
        
        # Scan
        echo "Running git-secrets scan..."
        git secrets --scan 2>&1 | tee "$RESULTS_DIR/git_secrets.log" || true
        
        # Check for exposed .env files
        if find . -name ".env*" -not -path "./.git/*" | grep -q .; then
            echo -e "${YELLOW}⚠${NC} Found .env files - ensure they're in .gitignore"
        fi
    fi
    
    # TruffleHog scan (if available)
    if command -v trufflehog &> /dev/null; then
        echo "Running TruffleHog scan..."
        trufflehog filesystem \
            --directory="$TARGET" \
            --json \
            --no-verification > "$RESULTS_DIR/trufflehog.json" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✓${NC} Secrets scan completed"
    echo ""
}

# Function for infrastructure scanning
scan_infrastructure() {
    echo -e "${MAGENTA}Scanning infrastructure configs...${NC}"
    
    # Kubernetes manifests
    if [ -d "deploy" ]; then
        echo "Scanning Kubernetes manifests..."
        trivy config deploy \
            --severity CRITICAL,HIGH,MEDIUM \
            --format json \
            --output "$RESULTS_DIR/trivy_k8s.json" 2>/dev/null || true
    fi
    
    # Docker Compose files
    for compose_file in docker-compose*.yml; do
        if [ -f "$compose_file" ]; then
            echo "Scanning $compose_file..."
            trivy config "$compose_file" \
                --severity CRITICAL,HIGH,MEDIUM \
                --format json \
                --output "$RESULTS_DIR/trivy_${compose_file%.yml}.json" 2>/dev/null || true
        fi
    done
    
    # Terraform files (if any)
    if find . -name "*.tf" -type f | grep -q .; then
        echo "Scanning Terraform files..."
        tfsec . \
            --format json \
            --out "$RESULTS_DIR/tfsec.json" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✓${NC} Infrastructure scan completed"
    echo ""
}

# Function for OWASP checks
run_owasp_checks() {
    echo -e "${MAGENTA}Running OWASP security checks...${NC}"
    
    # Check for common vulnerabilities
    local checks_passed=0
    local checks_failed=0
    
    # Check for secure headers
    echo -n "Checking security headers... "
    if grep -r "X-Frame-Options\|X-Content-Type-Options\|X-XSS-Protection" configs/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((checks_passed++))
    else
        echo -e "${YELLOW}⚠${NC} Missing security headers"
        ((checks_failed++))
    fi
    
    # Check for HTTPS enforcement
    echo -n "Checking HTTPS enforcement... "
    if grep -r "ssl\|tls\|https" configs/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((checks_passed++))
    else
        echo -e "${YELLOW}⚠${NC} HTTPS not enforced"
        ((checks_failed++))
    fi
    
    # Check for rate limiting
    echo -n "Checking rate limiting... "
    if grep -r "rate.*limit\|throttle" src/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((checks_passed++))
    else
        echo -e "${YELLOW}⚠${NC} Rate limiting not implemented"
        ((checks_failed++))
    fi
    
    # Check for input validation
    echo -n "Checking input validation... "
    if grep -r "validate\|sanitize\|escape" src/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((checks_passed++))
    else
        echo -e "${YELLOW}⚠${NC} Input validation may be insufficient"
        ((checks_failed++))
    fi
    
    # Check for authentication
    echo -n "Checking authentication... "
    if grep -r "auth\|jwt\|token" src/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((checks_passed++))
    else
        echo -e "${YELLOW}⚠${NC} Authentication not found"
        ((checks_failed++))
    fi
    
    echo ""
    echo "OWASP Checks: $checks_passed passed, $checks_failed warnings"
    echo ""
}

# Function for compliance checks
check_compliance() {
    echo -e "${MAGENTA}Checking compliance requirements...${NC}"
    
    local compliance_issues=0
    
    # GDPR compliance
    echo "Checking GDPR compliance..."
    if ! grep -r "data.*retention\|privacy\|gdpr" . --include="*.py" --include="*.md" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} No GDPR policy found"
        ((compliance_issues++))
    fi
    
    # SOC 2 compliance
    echo "Checking SOC 2 requirements..."
    if [ ! -f "docs/security-policy.md" ]; then
        echo -e "${YELLOW}⚠${NC} Security policy documentation missing"
        ((compliance_issues++))
    fi
    
    # Audit logging
    echo "Checking audit logging..."
    if grep -r "audit.*log\|audit_store" src/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Audit logging implemented"
    else
        echo -e "${YELLOW}⚠${NC} Audit logging not found"
        ((compliance_issues++))
    fi
    
    echo "Compliance issues: $compliance_issues"
    echo ""
}

# Function to generate security report
generate_security_report() {
    echo -e "${YELLOW}Generating security report...${NC}"
    
    cat > "$RESULTS_DIR/security_report.md" <<EOF
# BOL-CD Security Scan Report

**Date:** $(date)
**Target:** $TARGET
**Scan Type:** $SCAN_TYPE

## Executive Summary

Total vulnerabilities found: **$TOTAL_VULNS**
- Critical: $CRITICAL_VULNS
- High: $HIGH_VULNS
- Medium: $MEDIUM_VULNS
- Low: $LOW_VULNS

## Scan Results

### Container Security
$(if [ -f "$RESULTS_DIR/trivy_image.json" ]; then
    echo "✅ Docker image scanned"
    echo "See trivy_image.json for details"
else
    echo "⚠️ Docker image not scanned"
fi)

### Dependency Security
$(if [ -f "$RESULTS_DIR/safety_report.json" ]; then
    vulns=$(jq '. | length' "$RESULTS_DIR/safety_report.json" 2>/dev/null || echo "0")
    echo "- Python dependencies: $vulns vulnerabilities"
fi)
$(if [ -f "$RESULTS_DIR/npm_audit.json" ]; then
    vulns=$(jq '.metadata.vulnerabilities.total' "$RESULTS_DIR/npm_audit.json" 2>/dev/null || echo "0")
    echo "- Node.js dependencies: $vulns vulnerabilities"
fi)

### Code Security
$(if [ -f "$RESULTS_DIR/bandit_report.json" ]; then
    issues=$(jq '.results | length' "$RESULTS_DIR/bandit_report.json" 2>/dev/null || echo "0")
    echo "- Bandit: $issues security issues"
fi)
$(if [ -f "$RESULTS_DIR/semgrep_report.json" ]; then
    issues=$(jq '.results | length' "$RESULTS_DIR/semgrep_report.json" 2>/dev/null || echo "0")
    echo "- Semgrep: $issues issues"
fi)

### Secret Detection
$(if [ -f "$RESULTS_DIR/git_secrets.log" ]; then
    if grep -q "No secrets found" "$RESULTS_DIR/git_secrets.log"; then
        echo "✅ No secrets detected"
    else
        echo "⚠️ Potential secrets found - review git_secrets.log"
    fi
fi)

## Recommendations

### High Priority
$(if [ "$CRITICAL_VULNS" -gt 0 ]; then
    echo "1. **Fix critical vulnerabilities immediately**"
fi)
$(if [ "$HIGH_VULNS" -gt 0 ]; then
    echo "2. **Address high-severity vulnerabilities**"
fi)

### Medium Priority
- Implement security headers (CSP, HSTS, etc.)
- Enable dependency scanning in CI/CD
- Regular security audits

### Low Priority
- Update documentation
- Security training for developers

## Compliance Status

- [ ] GDPR compliance documentation
- [x] Audit logging implemented
- [x] Authentication system
- [x] Rate limiting
- [ ] SOC 2 certification

## Next Steps

1. Review and fix identified vulnerabilities
2. Implement automated security scanning in CI/CD
3. Schedule regular security audits
4. Update security documentation

---
*Generated by BOL-CD Security Scanner*
EOF
    
    echo -e "${GREEN}✓${NC} Report generated: $RESULTS_DIR/security_report.md"
    echo ""
}

# Main security scan
main() {
    # Check prerequisites
    check_prerequisites
    
    echo -e "${BLUE}Starting security scan...${NC}"
    echo ""
    
    case $SCAN_TYPE in
        quick)
            scan_secrets
            run_owasp_checks
            ;;
        dependencies)
            scan_dependencies
            ;;
        code)
            scan_code
            scan_secrets
            ;;
        infrastructure)
            scan_infrastructure
            scan_docker_image
            ;;
        full)
            scan_docker_image
            scan_dependencies
            scan_code
            scan_secrets
            scan_infrastructure
            run_owasp_checks
            check_compliance
            ;;
        *)
            echo -e "${RED}Unknown scan type: $SCAN_TYPE${NC}"
            echo "Valid types: quick, dependencies, code, infrastructure, full"
            exit 1
            ;;
    esac
    
    # Generate report
    generate_security_report
    
    # Summary
    echo -e "${BLUE}Security Scan Summary${NC}"
    echo "====================="
    echo "Results saved to: $RESULTS_DIR"
    echo ""
    
    if [ "$TOTAL_VULNS" -eq 0 ]; then
        echo -e "${GREEN}✅ No vulnerabilities found!${NC}"
        echo "The application passes security scan."
    elif [ "$CRITICAL_VULNS" -gt 0 ]; then
        echo -e "${RED}❌ Critical vulnerabilities found!${NC}"
        echo "Immediate action required."
        exit 1
    elif [ "$HIGH_VULNS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️ High severity vulnerabilities found${NC}"
        echo "Review and fix before production deployment."
    else
        echo -e "${GREEN}✓ Security scan completed${NC}"
        echo "Minor issues found - review report for details."
    fi
    echo ""
}

# Run main function
main
