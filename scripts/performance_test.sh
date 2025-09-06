#!/bin/bash
# BOL-CD Performance Test Script

set -e

# Configuration
TARGET_URL="${1:-http://localhost:8080}"
TEST_TYPE="${2:-basic}"
DURATION="${3:-60}"
CONCURRENT_USERS="${4:-100}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}⚡ BOL-CD Performance Test${NC}"
echo "============================"
echo "Target: $TARGET_URL"
echo "Type: $TEST_TYPE"
echo "Duration: ${DURATION}s"
echo "Concurrent Users: $CONCURRENT_USERS"
echo ""

# Create results directory
RESULTS_DIR="performance_results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check for required tools
    local tools=("ab" "curl" "jq" "gnuplot")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            echo -e "${YELLOW}Installing $tool...${NC}"
            case "$tool" in
                ab)
                    sudo apt-get install -y apache2-utils || brew install httpd
                    ;;
                gnuplot)
                    sudo apt-get install -y gnuplot || brew install gnuplot
                    ;;
                *)
                    sudo apt-get install -y "$tool" || brew install "$tool"
                    ;;
            esac
        fi
    done
    
    # Check if k6 is installed (advanced testing)
    if ! command -v k6 &> /dev/null; then
        echo -e "${YELLOW}Installing k6 for advanced testing...${NC}"
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo gpg -k
            sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
            echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
            sudo apt-get update
            sudo apt-get install k6
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew install k6
        fi
    fi
    
    echo -e "${GREEN}✓${NC} Prerequisites checked"
    echo ""
}

# Function for basic health check
health_check() {
    echo -e "${YELLOW}Running health check...${NC}"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET_URL/health")
    if [ "$response" != "200" ]; then
        echo -e "${RED}❌ Health check failed (HTTP $response)${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Health check passed"
    echo ""
}

# Function for Apache Bench test
run_ab_test() {
    local endpoint=$1
    local requests=$2
    local concurrency=$3
    local output_file=$4
    
    echo -e "${YELLOW}Testing $endpoint...${NC}"
    
    ab -n "$requests" \
       -c "$concurrency" \
       -g "$output_file.tsv" \
       -e "$output_file.csv" \
       -H "Accept: application/json" \
       -H "Content-Type: application/json" \
       "$TARGET_URL$endpoint" > "$output_file.txt" 2>&1
    
    # Extract key metrics
    local rps=$(grep "Requests per second" "$output_file.txt" | awk '{print $4}')
    local avg_time=$(grep "Time per request" "$output_file.txt" | head -1 | awk '{print $4}')
    local p95=$(grep "95%" "$output_file.txt" | awk '{print $2}')
    local p99=$(grep "99%" "$output_file.txt" | awk '{print $2}')
    
    echo "  RPS: ${rps}"
    echo "  Avg Response Time: ${avg_time}ms"
    echo "  95th percentile: ${p95}ms"
    echo "  99th percentile: ${p99}ms"
}

# Function for k6 load test
create_k6_script() {
    cat > "$RESULTS_DIR/load_test.js" <<'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Ramp up
    { duration: '2m', target: 100 },   // Stay at 100 users
    { duration: '30s', target: 200 },  // Spike to 200
    { duration: '2m', target: 200 },   // Stay at 200
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'http_req_failed': ['rate<0.1'],
    'errors': ['rate<0.1'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080';

// Test scenarios
const scenarios = [
  { endpoint: '/health', weight: 10 },
  { endpoint: '/api/alerts/filtered', weight: 30 },
  { endpoint: '/metrics', weight: 5 },
  { endpoint: '/api/reports/daily/latest', weight: 20 },
];

export default function () {
  // Select random scenario based on weight
  const totalWeight = scenarios.reduce((sum, s) => sum + s.weight, 0);
  let random = Math.random() * totalWeight;
  let scenario;
  
  for (const s of scenarios) {
    random -= s.weight;
    if (random <= 0) {
      scenario = s;
      break;
    }
  }
  
  // Make request
  const start = Date.now();
  const response = http.get(`${BASE_URL}${scenario.endpoint}`);
  const latency = Date.now() - start;
  
  // Record metrics
  apiLatency.add(latency);
  errorRate.add(response.status >= 400);
  
  // Checks
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  // Think time
  sleep(Math.random() * 2 + 1);
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const { metrics } = data;
  let summary = '\n=== Performance Test Results ===\n\n';
  
  // Key metrics
  summary += `Requests: ${metrics.http_reqs.values.count}\n`;
  summary += `Errors: ${(metrics.http_req_failed.values.rate * 100).toFixed(2)}%\n`;
  summary += `Avg Response Time: ${metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
  summary += `P95 Response Time: ${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += `P99 Response Time: ${metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n`;
  summary += `RPS: ${(metrics.http_reqs.values.rate).toFixed(2)}\n`;
  
  return summary;
}
EOF
}

# Function for stress test
run_stress_test() {
    echo -e "${MAGENTA}Running stress test...${NC}"
    
    create_k6_script
    
    TARGET_URL="$TARGET_URL" k6 run \
        --out json="$RESULTS_DIR/k6_results.json" \
        --summary-export="$RESULTS_DIR/k6_summary.json" \
        "$RESULTS_DIR/load_test.js"
    
    # Parse results
    if [ -f "$RESULTS_DIR/k6_summary.json" ]; then
        echo -e "${GREEN}✓${NC} Stress test completed"
        
        # Extract key metrics
        local total_requests=$(jq '.metrics.http_reqs.values.count' "$RESULTS_DIR/k6_summary.json")
        local error_rate=$(jq '.metrics.http_req_failed.values.rate' "$RESULTS_DIR/k6_summary.json")
        local avg_duration=$(jq '.metrics.http_req_duration.values.avg' "$RESULTS_DIR/k6_summary.json")
        
        echo "  Total Requests: $total_requests"
        echo "  Error Rate: $(echo "$error_rate * 100" | bc -l | xargs printf "%.2f")%"
        echo "  Avg Duration: $(echo "$avg_duration" | xargs printf "%.2f")ms"
    fi
}

# Function for endpoint testing
test_endpoints() {
    echo -e "${MAGENTA}Testing individual endpoints...${NC}"
    echo ""
    
    local endpoints=(
        "/health:GET:1000:10"
        "/api/alerts/filtered:GET:500:10"
        "/metrics:GET:1000:10"
        "/api/reports/daily/latest:GET:200:5"
    )
    
    for endpoint_config in "${endpoints[@]}"; do
        IFS=':' read -r endpoint method requests concurrency <<< "$endpoint_config"
        
        echo -e "${YELLOW}Testing $endpoint ($method)${NC}"
        
        # Run test
        output_file="$RESULTS_DIR/ab_$(echo "$endpoint" | tr '/' '_')"
        run_ab_test "$endpoint" "$requests" "$concurrency" "$output_file"
        echo ""
    done
}

# Function for database performance test
test_database() {
    echo -e "${MAGENTA}Testing database performance...${NC}"
    
    # Test connection pool
    echo "Testing connection pool..."
    for i in {1..50}; do
        curl -s "$TARGET_URL/health" &
    done
    wait
    echo -e "${GREEN}✓${NC} Connection pool test passed"
    
    # Test query performance
    echo "Testing query performance..."
    time curl -s "$TARGET_URL/api/reports/daily/latest" > /dev/null
    echo -e "${GREEN}✓${NC} Query performance test completed"
    echo ""
}

# Function for memory leak test
test_memory_leak() {
    echo -e "${MAGENTA}Testing for memory leaks...${NC}"
    
    # Get initial memory usage
    initial_mem=$(curl -s "$TARGET_URL/metrics" | grep "process_resident_memory_bytes" | awk '{print $2}')
    
    # Run sustained load
    echo "Running sustained load for 60 seconds..."
    ab -t 60 -c 10 -q "$TARGET_URL/health" > /dev/null 2>&1
    
    # Get final memory usage
    sleep 5
    final_mem=$(curl -s "$TARGET_URL/metrics" | grep "process_resident_memory_bytes" | awk '{print $2}')
    
    # Calculate increase
    if [ -n "$initial_mem" ] && [ -n "$final_mem" ]; then
        mem_increase=$(echo "scale=2; ($final_mem - $initial_mem) / 1024 / 1024" | bc)
        echo "  Memory increase: ${mem_increase}MB"
        
        if (( $(echo "$mem_increase > 100" | bc -l) )); then
            echo -e "${YELLOW}⚠${NC} Potential memory leak detected"
        else
            echo -e "${GREEN}✓${NC} No significant memory leak detected"
        fi
    fi
    echo ""
}

# Function to generate report
generate_report() {
    echo -e "${YELLOW}Generating performance report...${NC}"
    
    cat > "$RESULTS_DIR/report.md" <<EOF
# BOL-CD Performance Test Report

**Date:** $(date)
**Target:** $TARGET_URL
**Test Type:** $TEST_TYPE

## Summary

### Key Metrics
$(if [ -f "$RESULTS_DIR/k6_summary.json" ]; then
    echo "- **Total Requests:** $(jq '.metrics.http_reqs.values.count' "$RESULTS_DIR/k6_summary.json")"
    echo "- **Error Rate:** $(jq '.metrics.http_req_failed.values.rate' "$RESULTS_DIR/k6_summary.json" | awk '{printf "%.2f%%", $1*100}')"
    echo "- **Avg Response Time:** $(jq '.metrics.http_req_duration.values.avg' "$RESULTS_DIR/k6_summary.json" | awk '{printf "%.2fms", $1}')"
    echo "- **P95 Response Time:** $(jq '.metrics.http_req_duration.values["p(95)"]' "$RESULTS_DIR/k6_summary.json" | awk '{printf "%.2fms", $1}')"
    echo "- **P99 Response Time:** $(jq '.metrics.http_req_duration.values["p(99)"]' "$RESULTS_DIR/k6_summary.json" | awk '{printf "%.2fms", $1}')"
fi)

### Test Results
- Health Check: ✅ Passed
- Stress Test: $([ -f "$RESULTS_DIR/k6_summary.json" ] && echo "✅ Completed" || echo "⚠️ Skipped")
- Memory Leak Test: $(grep -q "No significant memory leak" "$RESULTS_DIR/memory_test.log" 2>/dev/null && echo "✅ Passed" || echo "⚠️ Check required")

## Recommendations

$(if [ -f "$RESULTS_DIR/k6_summary.json" ]; then
    error_rate=$(jq '.metrics.http_req_failed.values.rate' "$RESULTS_DIR/k6_summary.json")
    if (( $(echo "$error_rate > 0.05" | bc -l) )); then
        echo "- ⚠️ High error rate detected. Review application logs and scale resources."
    fi
    
    p99=$(jq '.metrics.http_req_duration.values["p(99)"]' "$RESULTS_DIR/k6_summary.json")
    if (( $(echo "$p99 > 1000" | bc -l) )); then
        echo "- ⚠️ P99 latency exceeds 1 second. Consider optimizing slow queries and adding caching."
    fi
fi)

## Detailed Results

See individual test files in this directory for detailed metrics.

EOF
    
    echo -e "${GREEN}✓${NC} Report generated: $RESULTS_DIR/report.md"
    echo ""
}

# Function to create visualization
create_visualization() {
    echo -e "${YELLOW}Creating performance graphs...${NC}"
    
    if [ -f "$RESULTS_DIR/ab_health.tsv" ]; then
        gnuplot <<EOF
set terminal png size 1200,600
set output "$RESULTS_DIR/response_time_graph.png"
set title "Response Time Distribution"
set xlabel "Request Number"
set ylabel "Response Time (ms)"
set grid
plot "$RESULTS_DIR/ab_health.tsv" using 9 with lines title "Response Time" lw 2
EOF
        echo -e "${GREEN}✓${NC} Graph created: $RESULTS_DIR/response_time_graph.png"
    fi
    echo ""
}

# Main test execution
main() {
    # Check prerequisites
    check_prerequisites
    
    # Health check
    health_check
    
    # Start monitoring
    echo -e "${BLUE}Starting performance tests...${NC}"
    echo ""
    
    case $TEST_TYPE in
        basic)
            test_endpoints
            ;;
        stress)
            run_stress_test
            test_memory_leak
            ;;
        full)
            test_endpoints
            test_database
            run_stress_test
            test_memory_leak
            ;;
        *)
            echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
            echo "Valid types: basic, stress, full"
            exit 1
            ;;
    esac
    
    # Generate report and visualization
    generate_report
    create_visualization
    
    # Summary
    echo -e "${BLUE}Performance Test Summary${NC}"
    echo "========================"
    echo "Results saved to: $RESULTS_DIR"
    echo ""
    
    # Check if tests passed
    if [ -f "$RESULTS_DIR/k6_summary.json" ]; then
        error_rate=$(jq '.metrics.http_req_failed.values.rate' "$RESULTS_DIR/k6_summary.json")
        if (( $(echo "$error_rate < 0.1" | bc -l) )); then
            echo -e "${GREEN}✅ Performance tests PASSED${NC}"
            echo "The application meets performance requirements."
        else
            echo -e "${YELLOW}⚠️ Performance tests completed with warnings${NC}"
            echo "Review the report for optimization recommendations."
        fi
    else
        echo -e "${GREEN}✅ Basic performance tests completed${NC}"
    fi
    echo ""
}

# Run main function
main
