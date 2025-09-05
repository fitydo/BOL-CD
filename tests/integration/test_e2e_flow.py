"""
End-to-end integration tests for the condensed alerts system
"""
import pytest
import pytest_asyncio
import asyncio
import httpx
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Any

# Run all tests in this module with pytest-asyncio
pytestmark = pytest.mark.asyncio

# Ensure API keys are configured before importing the app (keys are read at import)
os.environ["BOLCD_API_KEYS"] = "admin:admin-key,condensed:test-key,full:full-key,ingest:ingest-key"
os.environ["BOLCD_HASH_METHOD"] = "plain"
os.environ["BOLCD_RATE_LIMIT_ENABLED"] = "0"

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://test")
API_KEY_ADMIN = os.getenv("TEST_API_KEY_ADMIN", "admin-key")
API_KEY_CONSUMER = os.getenv("TEST_API_KEY_CONSUMER", "test-key")


from src.bolcd.api.main import app


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client against the in-memory ASGI app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=API_BASE_URL) as client:
        yield client


@pytest_asyncio.fixture
async def cleanup_db():
    """Clean up test data after each test"""
    # Reset DB tables before each test for isolation
    from src.bolcd.db import engine
    from src.bolcd.models.condense import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


class TestE2EFlow:
    """End-to-end test scenarios"""
    
    @pytest.mark.usefixtures("cleanup_db")
    async def test_full_alert_processing_flow(self, client: httpx.AsyncClient):
        """Test the complete flow: ingest -> decide -> deliver/suppress -> late replay"""
        
        # Step 1: Ingest multiple alerts
        alerts = [
            {
                "ts": datetime.now().isoformat(),
                "entity_id": "host-001",
                "rule_id": "R-001",
                "severity": "low",
                "signature": "port_scan",
                "attrs": {"port": 22}
            },
            {
                "ts": (datetime.now() + timedelta(seconds=30)).isoformat(),
                "entity_id": "host-001",
                "rule_id": "R-002",
                "severity": "medium",
                "signature": "failed_login",
                "attrs": {"user": "admin"}
            },
            {
                "ts": (datetime.now() + timedelta(seconds=60)).isoformat(),
                "entity_id": "host-001",
                "rule_id": "R-003",
                "severity": "critical",
                "signature": "privilege_escalation",
                "attrs": {"process": "sudo"}
            }
        ]
        
        ingested_ids = []
        for alert in alerts:
            response = await client.post(
                "/v1/ingest",
                json=alert,
                headers={"X-API-Key": API_KEY_ADMIN}
            )
            assert response.status_code == 200
            result = response.json()
            ingested_ids.append(result["alert_id"])
            print(f"Ingested alert {result['alert_id']}: decision={result['decision']}")
        
        # Step 2: Check condensed view
        response = await client.get(
            "/v1/alerts?view=condensed",
            headers={"X-API-Key": API_KEY_CONSUMER}
        )
        assert response.status_code == 200
        condensed = response.json()
        assert "alerts" in condensed
        print(f"Condensed view: {len(condensed['alerts'])} alerts delivered")
        
        # Critical alerts should always be delivered
        critical_found = any(
            a["severity"] == "critical" 
            for a in condensed["alerts"]
        )
        assert critical_found, "Critical alert should be in condensed view"
        
        # Step 3: Check full view (admin only)
        response = await client.get(
            "/v1/alerts?view=full",
            headers={"X-API-Key": API_KEY_ADMIN}
        )
        assert response.status_code == 200
        full = response.json()
        assert len(full["alerts"]) == len(alerts)
        print(f"Full view: {len(full['alerts'])} total alerts")
        
        # Step 4: Get explanation for a specific alert
        if ingested_ids:
            response = await client.get(
                f"/v1/alerts/{ingested_ids[0]}/explain",
                headers={"X-API-Key": API_KEY_CONSUMER}
            )
            assert response.status_code == 200
            explanation = response.json()
            assert "decision" in explanation
            assert "type" in explanation["decision"]
            print(f"Alert {ingested_ids[0]} explanation: {explanation}")
        
        # Step 5: Check late replay (may be empty initially)
        response = await client.get(
            "/v1/alerts/late",
            headers={"X-API-Key": API_KEY_CONSUMER}
        )
        assert response.status_code == 200
        late = response.json()
        print(f"Late replay: {len(late.get('alerts', []))} alerts")
    
    @pytest.mark.usefixtures("cleanup_db")
    async def test_high_severity_protection(self, client: httpx.AsyncClient):
        """Test that high/critical severity alerts are never suppressed"""
        
        severities = ["low", "medium", "high", "critical"]
        results = {}
        
        for severity in severities:
            alert = {
                "ts": datetime.now().isoformat(),
                "entity_id": f"host-{severity}",
                "rule_id": f"R-{severity}",
                "severity": severity,
                "signature": f"test_{severity}",
                "attrs": {"test": True}
            }
            
            response = await client.post(
                "/v1/ingest",
                json=alert,
                headers={"X-API-Key": API_KEY_ADMIN}
            )
            assert response.status_code == 200
            result = response.json()
            results[severity] = result["decision"]
        
        # High and critical should always be delivered
        assert results["high"] == "deliver", "High severity should be delivered"
        assert results["critical"] == "deliver", "Critical severity should be delivered"
        print(f"Severity protection test results: {results}")
    
    async def test_api_key_scopes(self, client: httpx.AsyncClient):
        """Test API key scope enforcement"""
        
        # Test consumer key - should access condensed view
        response = await client.get(
            "/v1/alerts?view=condensed",
            headers={"X-API-Key": API_KEY_CONSUMER}
        )
        assert response.status_code == 200
        
        # Test consumer key - should NOT access full view
        response = await client.get(
            "/v1/alerts?view=full",
            headers={"X-API-Key": API_KEY_CONSUMER}
        )
        assert response.status_code == 403
        
        # Test admin key - should access everything
        response = await client.get(
            "/v1/alerts?view=full",
            headers={"X-API-Key": API_KEY_ADMIN}
        )
        assert response.status_code == 200
        
        # Test invalid key
        response = await client.get(
            "/v1/alerts?view=condensed",
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401
        
        print("API key scope tests passed")
    
    @pytest.mark.usefixtures("cleanup_db")
    async def test_near_window_suppression(self, client: httpx.AsyncClient):
        """Test that correlated alerts within near window are suppressed"""
        
        base_time = datetime.now()
        
        # First alert (root)
        alert1 = {
            "ts": base_time.isoformat(),
            "entity_id": "host-corr",
            "rule_id": "R-100",
            "severity": "medium",
            "signature": "initial_event",
            "attrs": {}
        }
        
        # Second alert (should be suppressed if correlated)
        alert2 = {
            "ts": (base_time + timedelta(seconds=30)).isoformat(),
            "entity_id": "host-corr",
            "rule_id": "R-101",
            "severity": "medium",
            "signature": "correlated_event",
            "attrs": {}
        }
        
        # Ingest both
        response1 = await client.post(
            "/v1/ingest",
            json=alert1,
            headers={"X-API-Key": API_KEY_ADMIN}
        )
        assert response1.status_code == 200
        result1 = response1.json()
        
        response2 = await client.post(
            "/v1/ingest",
            json=alert2,
            headers={"X-API-Key": API_KEY_ADMIN}
        )
        assert response2.status_code == 200
        result2 = response2.json()
        
        print(f"Alert 1: {result1['decision']}, Alert 2: {result2['decision']}")
        
        # Check condensed view
        response = await client.get(
            "/v1/alerts?view=condensed",
            headers={"X-API-Key": API_KEY_CONSUMER}
        )
        assert response.status_code == 200
        condensed = response.json()
        
        # Count how many from this entity made it through
        entity_alerts = [
            a for a in condensed["alerts"] 
            if a["entity_id"] == "host-corr"
        ]
        print(f"Condensed alerts for host-corr: {len(entity_alerts)}")
    
    @pytest.mark.usefixtures("cleanup_db")
    async def test_performance_under_load(self, client: httpx.AsyncClient):
        """Test system performance under load"""
        
        num_alerts = 100
        batch_size = 10  # Limit concurrent requests to avoid connection pool exhaustion
        start_time = datetime.now()
        
        # Generate and send alerts concurrently
        async def send_alert(i: int):
            alert = {
                "ts": datetime.now().isoformat(),
                "entity_id": f"host-{i % 10}",
                "rule_id": f"R-{i % 50}",
                "severity": ["low", "medium", "high"][i % 3],
                "signature": f"event_{i % 20}",
                "attrs": {"index": i}
            }
            
            response = await client.post(
                "/v1/ingest",
                json=alert,
                headers={"X-API-Key": API_KEY_ADMIN}
            )
            return response.status_code == 200
        
        # Send alerts in batches to avoid connection pool exhaustion
        results = []
        for batch_start in range(0, num_alerts, batch_size):
            batch_end = min(batch_start + batch_size, num_alerts)
            batch_tasks = [send_alert(i) for i in range(batch_start, batch_end)]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        assert all(results), "Some alerts failed to ingest"
        assert duration < 10, f"Ingesting {num_alerts} alerts took too long: {duration}s"
        
        print(f"Performance test: {num_alerts} alerts in {duration:.2f}s")
        print(f"Throughput: {num_alerts/duration:.2f} alerts/sec")
        
        # Check metrics endpoint
        response = await client.get("/metrics")
        assert response.status_code == 200
        metrics = response.text
        assert "bolcd_suppress_total" in metrics
        assert "bolcd_decision_latency_seconds" in metrics


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=API_BASE_URL) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        health = response.json()
        assert health["status"] == "healthy"
        print(f"Health check: {health}")


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test Prometheus metrics endpoint"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=API_BASE_URL) as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        metrics = response.text
        expected_metrics = [
            "bolcd_suppress_total",
            "bolcd_late_replay_total",
            "bolcd_false_suppression_total",
            "bolcd_decision_latency_seconds"
        ]
        
        for metric in expected_metrics:
            assert metric in metrics, f"Metric {metric} not found"
        
        print("All expected metrics found")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_health_check())
    asyncio.run(test_metrics_endpoint())
