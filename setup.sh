#!/bin/bash
# BOL-CD Quick Setup Script
# This script sets up the environment for demo/development

set -e

echo "========================================="
echo "  BOL-CD Quick Setup"
echo "========================================="

# Check if running in correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Please run this script from the BOL-CD root directory"
    exit 1
fi

# 1. Create .env file from template
echo "📝 Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp env.example .env
    echo "✅ Created .env file from template"
    echo "   Please edit .env to add your specific configurations"
else
    echo "⚠️  .env file already exists, skipping..."
fi

# 2. Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -e . --quiet
pip install python3-saml cryptography psycopg2-binary --quiet
echo "✅ Python dependencies installed"

# 3. Create configuration files
echo ""
echo "📋 Creating configuration files..."

# Create retention policy config
mkdir -p configs
cat > configs/retention.yaml << EOF
# Data Retention Policy Configuration
# Adjust retention periods based on your compliance requirements

retention_policies:
  alerts:
    retention_days: 90
    enabled: true
    archive_before_delete: false
    compliance_hold: false
  
  audit_logs:
    retention_days: 365
    enabled: true
    archive_before_delete: true
    compliance_hold: false
  
  metrics:
    retention_days: 30
    enabled: true
    archive_before_delete: false
    compliance_hold: false
  
  reports:
    retention_days: 365
    enabled: true
    archive_before_delete: true
    compliance_hold: false
  
  temporary:
    retention_days: 7
    enabled: true
    archive_before_delete: false
    compliance_hold: false
  
  compliance:
    retention_days: 2555  # 7 years
    enabled: false
    archive_before_delete: true
    compliance_hold: true
EOF

echo "✅ Created configs/retention.yaml"

# Create SLA config
cat > configs/sla.yaml << EOF
# SLA Target Configuration
# Define your service level objectives

sla_targets:
  uptime:
    value: 99.5
    unit: "%"
    window_seconds: 86400  # 24 hours
    critical: true
  
  availability:
    value: 99.9
    unit: "%"
    window_seconds: 2592000  # 30 days
    critical: true
  
  response_p95:
    value: 0.1  # 100ms
    unit: "seconds"
    window_seconds: 3600  # 1 hour
    critical: false
  
  response_p99:
    value: 0.5  # 500ms
    unit: "seconds"
    window_seconds: 3600
    critical: false
  
  error_rate:
    value: 0.5
    unit: "%"
    window_seconds: 3600
    critical: false
  
  throughput:
    value: 10000
    unit: "eps"
    window_seconds: 60
    critical: false
EOF

echo "✅ Created configs/sla.yaml"

# 4. Create data directories
echo ""
echo "📁 Creating data directories..."
mkdir -p data/{alerts,audit,metrics,reports,tmp,tenants,sla}
mkdir -p backups
echo "✅ Data directories created"

# 5. Initialize database
echo ""
echo "🗄️  Initializing database..."
python -c "
from src.bolcd.auth.manager import AuthManager
auth = AuthManager()
print('✅ Authentication database initialized')
print('✅ Demo accounts created:')
print('   - admin@demo.com / admin123')
print('   - user@demo.com / user123')
print('   - analyst@demo.com / analyst123')
" 2>/dev/null || echo "⚠️  Database initialization skipped (may already exist)"

# 6. Setup Web UI dependencies
echo ""
echo "🌐 Setting up Web UI..."
if [ -d "web" ]; then
    cd web
    if [ ! -d "node_modules" ]; then
        echo "Installing npm packages..."
        npm install --quiet
        echo "✅ Web UI dependencies installed"
    else
        echo "⚠️  node_modules already exists, skipping npm install"
    fi
    cd ..
else
    echo "⚠️  Web directory not found, skipping Web UI setup"
fi

# 7. Generate quick start script
cat > start.sh << 'EOF'
#!/bin/bash
# Quick start script for BOL-CD

echo "Starting BOL-CD services..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start API server
echo "🚀 Starting API server on port 8080..."
PYTHONPATH="${PYTHONPATH}:src" uvicorn src.bolcd.api.app:app --host 0.0.0.0 --port 8080 --reload &
API_PID=$!

# Start Web UI
if [ -d "web" ]; then
    echo "🌐 Starting Web UI on port 3000..."
    cd web && npm run dev &
    WEB_PID=$!
    cd ..
fi

echo ""
echo "========================================="
echo "  BOL-CD is running!"
echo "========================================="
echo "  API:    http://localhost:8080"
echo "  Web UI: http://localhost:3000"
echo "  Docs:   http://localhost:8080/docs"
echo ""
echo "  Demo accounts:"
echo "  - admin@demo.com / admin123"
echo "  - user@demo.com / user123"
echo "  - analyst@demo.com / analyst123"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $API_PID $WEB_PID 2>/dev/null; exit" INT
wait
EOF

chmod +x start.sh
echo "✅ Created start.sh script"

echo ""
echo "========================================="
echo "  Setup Complete! 🎉"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Review and edit .env file for your environment"
echo "2. Run './start.sh' to start all services"
echo "3. Access the Web UI at http://localhost:3000"
echo "4. Access the API docs at http://localhost:8080/docs"
echo ""
echo "For production deployment:"
echo "- Update .env with production values"
echo "- Set BOLCD_PLAN_TIER to your subscription level"
echo "- Configure real SIEM connections"
echo "- Set up proper SSL/TLS certificates"
echo "- Configure PostgreSQL instead of SQLite"
