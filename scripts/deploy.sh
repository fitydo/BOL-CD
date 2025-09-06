#!/bin/bash
# BOL-CD Deployment Script

set -e

# Configuration
ENVIRONMENT="${1:-staging}"
VERSION="${2:-latest}"
NAMESPACE="${3:-bolcd}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 BOL-CD Deployment Script${NC}"
echo "================================"
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"
echo "Namespace: $NAMESPACE"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Docker found"
    
    # Check kubectl (for Kubernetes deployment)
    if [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "kubernetes" ]; then
        if ! command -v kubectl &> /dev/null; then
            echo -e "${RED}❌ kubectl is not installed${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓${NC} kubectl found"
        
        # Check Helm
        if ! command -v helm &> /dev/null; then
            echo -e "${RED}❌ Helm is not installed${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓${NC} Helm found"
    fi
    
    echo ""
}

# Function to build Docker image
build_image() {
    echo -e "${YELLOW}Building Docker image...${NC}"
    
    docker build -t bolcd:$VERSION .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Docker image built successfully"
    else
        echo -e "${RED}❌ Docker build failed${NC}"
        exit 1
    fi
    echo ""
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}Running tests...${NC}"
    
    # Run unit tests
    docker run --rm bolcd:$VERSION python -m pytest tests/unit -v
    
    # Run integration tests
    docker run --rm --network host bolcd:$VERSION python -m pytest tests/integration -v
    
    # Run security scan
    echo "Running security scan..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image bolcd:$VERSION
    
    echo -e "${GREEN}✓${NC} All tests passed"
    echo ""
}

# Function to deploy to Docker Compose
deploy_docker_compose() {
    echo -e "${YELLOW}Deploying with Docker Compose...${NC}"
    
    # Create secrets directory
    mkdir -p secrets
    
    # Generate secrets if not exist
    if [ ! -f secrets/db_password.txt ]; then
        openssl rand -base64 32 > secrets/db_password.txt
        echo "Generated database password"
    fi
    
    if [ ! -f secrets/redis_password.txt ]; then
        openssl rand -base64 32 > secrets/redis_password.txt
        echo "Generated Redis password"
    fi
    
    # Use appropriate compose file
    if [ "$ENVIRONMENT" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.yml"
    fi
    
    # Deploy
    docker-compose -f $COMPOSE_FILE up -d
    
    # Wait for services to be healthy
    echo "Waiting for services to be healthy..."
    sleep 10
    
    # Check health
    docker-compose -f $COMPOSE_FILE ps
    
    echo -e "${GREEN}✓${NC} Docker Compose deployment complete"
    echo ""
}

# Function to deploy to Kubernetes
deploy_kubernetes() {
    echo -e "${YELLOW}Deploying to Kubernetes...${NC}"
    
    # Create namespace if not exists
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secrets
    kubectl create secret generic bolcd-secrets \
        --from-literal=database-url="$DATABASE_URL" \
        --from-literal=redis-url="$REDIS_URL" \
        --from-literal=jwt-secret="$(openssl rand -base64 32)" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy with Helm
    helm upgrade --install bolcd ./deploy/helm/bolcd \
        --namespace $NAMESPACE \
        --set image.tag=$VERSION \
        --set ingress.hosts[0].host=$BOLCD_DOMAIN \
        --wait \
        --timeout 10m
    
    # Check deployment status
    kubectl rollout status deployment/bolcd -n $NAMESPACE
    
    echo -e "${GREEN}✓${NC} Kubernetes deployment complete"
    echo ""
}

# Function to run health checks
health_check() {
    echo -e "${YELLOW}Running health checks...${NC}"
    
    if [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "kubernetes" ]; then
        # Kubernetes health check
        HEALTH_URL="https://$BOLCD_DOMAIN/health"
    else
        # Docker Compose health check
        HEALTH_URL="http://localhost:8080/health"
    fi
    
    # Wait for service to be ready
    for i in {1..30}; do
        if curl -s -f $HEALTH_URL > /dev/null; then
            echo -e "${GREEN}✓${NC} Health check passed"
            break
        fi
        echo "Waiting for service to be ready... ($i/30)"
        sleep 5
    done
    
    # API test
    echo "Testing API endpoints..."
    curl -s $HEALTH_URL | jq .
    
    echo ""
}

# Function to setup monitoring
setup_monitoring() {
    echo -e "${YELLOW}Setting up monitoring...${NC}"
    
    if [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "kubernetes" ]; then
        # Get Grafana password
        GRAFANA_PASSWORD=$(kubectl get secret --namespace $NAMESPACE bolcd-grafana -o jsonpath="{.data.admin-password}" | base64 --decode)
        echo "Grafana admin password: $GRAFANA_PASSWORD"
        echo "Grafana URL: https://$BOLCD_DOMAIN:3030"
    else
        echo "Grafana URL: http://localhost:3030"
        echo "Default credentials: admin/changeme"
    fi
    
    echo -e "${GREEN}✓${NC} Monitoring setup complete"
    echo ""
}

# Function to show deployment info
show_info() {
    echo -e "${BLUE}Deployment Information${NC}"
    echo "======================"
    
    if [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "kubernetes" ]; then
        echo "Application URL: https://$BOLCD_DOMAIN"
        echo "API URL: https://$BOLCD_DOMAIN/api"
        echo "Metrics URL: https://$BOLCD_DOMAIN/metrics"
        
        # Get pod information
        kubectl get pods -n $NAMESPACE
        
        # Get service information
        kubectl get svc -n $NAMESPACE
    else
        echo "Application URL: http://localhost"
        echo "API URL: http://localhost:8080"
        echo "Grafana URL: http://localhost:3030"
        echo "Prometheus URL: http://localhost:9091"
        
        # Show Docker containers
        docker-compose ps
    fi
    
    echo ""
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
}

# Main deployment flow
main() {
    check_prerequisites
    
    # Build image
    build_image
    
    # Run tests
    if [ "$ENVIRONMENT" != "development" ]; then
        run_tests
    fi
    
    # Deploy based on environment
    case $ENVIRONMENT in
        development|staging)
            deploy_docker_compose
            ;;
        production|kubernetes)
            deploy_kubernetes
            ;;
        *)
            echo -e "${RED}Unknown environment: $ENVIRONMENT${NC}"
            echo "Valid environments: development, staging, production, kubernetes"
            exit 1
            ;;
    esac
    
    # Health check
    health_check
    
    # Setup monitoring
    setup_monitoring
    
    # Show deployment info
    show_info
}

# Run main function
main
