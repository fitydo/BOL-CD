#!/usr/bin/env python3
"""
Generate realistic security events based on common SIEM patterns
"""
import json
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Real-world security event patterns from enterprise environments
SECURITY_PATTERNS = [
    # Authentication Events
    {"signature": "Failed_Login_Attempt", "severity": "medium", "category": "authentication", "source": "auth.log", "frequency": 30},
    {"signature": "Successful_Login", "severity": "low", "category": "authentication", "source": "auth.log", "frequency": 100},
    {"signature": "Account_Lockout", "severity": "high", "category": "authentication", "source": "auth.log", "frequency": 5},
    {"signature": "Password_Reset", "severity": "low", "category": "authentication", "source": "auth.log", "frequency": 10},
    {"signature": "Privilege_Escalation_Attempt", "severity": "critical", "category": "authentication", "source": "auth.log", "frequency": 2},
    
    # Network Security
    {"signature": "Port_Scan_Detected", "severity": "medium", "category": "network", "source": "firewall", "frequency": 20},
    {"signature": "DDoS_Attack_Suspected", "severity": "critical", "category": "network", "source": "firewall", "frequency": 1},
    {"signature": "Unusual_Outbound_Traffic", "severity": "high", "category": "network", "source": "firewall", "frequency": 8},
    {"signature": "Blocked_Connection", "severity": "low", "category": "network", "source": "firewall", "frequency": 50},
    {"signature": "VPN_Connection_Established", "severity": "low", "category": "network", "source": "vpn.log", "frequency": 40},
    
    # Web Application Security
    {"signature": "SQL_Injection_Attempt", "severity": "critical", "category": "web", "source": "waf", "frequency": 3},
    {"signature": "XSS_Attack_Detected", "severity": "high", "category": "web", "source": "waf", "frequency": 5},
    {"signature": "Directory_Traversal_Attempt", "severity": "high", "category": "web", "source": "waf", "frequency": 4},
    {"signature": "Bot_Activity_Detected", "severity": "low", "category": "web", "source": "waf", "frequency": 30},
    {"signature": "Rate_Limit_Exceeded", "severity": "medium", "category": "web", "source": "waf", "frequency": 15},
    
    # Endpoint Security
    {"signature": "Malware_Detected", "severity": "critical", "category": "endpoint", "source": "antivirus", "frequency": 2},
    {"signature": "Suspicious_Process_Execution", "severity": "high", "category": "endpoint", "source": "edr", "frequency": 10},
    {"signature": "Registry_Modification", "severity": "medium", "category": "endpoint", "source": "edr", "frequency": 20},
    {"signature": "USB_Device_Connected", "severity": "low", "category": "endpoint", "source": "endpoint", "frequency": 25},
    {"signature": "Software_Installation", "severity": "low", "category": "endpoint", "source": "endpoint", "frequency": 15},
    
    # Data Security
    {"signature": "Data_Exfiltration_Suspected", "severity": "critical", "category": "data", "source": "dlp", "frequency": 1},
    {"signature": "Sensitive_Data_Access", "severity": "high", "category": "data", "source": "dlp", "frequency": 5},
    {"signature": "Large_File_Transfer", "severity": "medium", "category": "data", "source": "dlp", "frequency": 10},
    {"signature": "Unauthorized_Database_Access", "severity": "critical", "category": "data", "source": "database", "frequency": 2},
    {"signature": "Database_Schema_Change", "severity": "medium", "category": "data", "source": "database", "frequency": 3},
    
    # Cloud Security
    {"signature": "S3_Bucket_Public_Access", "severity": "high", "category": "cloud", "source": "aws", "frequency": 2},
    {"signature": "IAM_Policy_Change", "severity": "medium", "category": "cloud", "source": "aws", "frequency": 5},
    {"signature": "EC2_Instance_Launched", "severity": "low", "category": "cloud", "source": "aws", "frequency": 10},
    {"signature": "Security_Group_Modified", "severity": "medium", "category": "cloud", "source": "aws", "frequency": 8},
    {"signature": "Root_Account_Usage", "severity": "critical", "category": "cloud", "source": "aws", "frequency": 1},
]

# Realistic host names
HOSTS = [
    # Web servers
    "web-prod-01.company.com", "web-prod-02.company.com", "web-prod-03.company.com",
    "web-staging-01.company.com", "web-dev-01.company.com",
    
    # Database servers
    "db-master-01.company.com", "db-slave-01.company.com", "db-slave-02.company.com",
    "db-analytics-01.company.com", "db-backup-01.company.com",
    
    # Application servers
    "app-server-01.company.com", "app-server-02.company.com", "app-server-03.company.com",
    "api-gateway-01.company.com", "api-gateway-02.company.com",
    
    # Infrastructure
    "proxy-01.company.com", "proxy-02.company.com",
    "mail-server-01.company.com", "file-server-01.company.com",
    "dc-01.company.com", "dc-02.company.com",
    
    # Cloud instances
    "ec2-prod-web-01", "ec2-prod-api-01", "ec2-prod-db-01",
    "aks-node-01", "aks-node-02", "gke-node-01",
    
    # Workstations
    "ws-john-doe", "ws-jane-smith", "ws-admin-01", "ws-dev-15",
    "laptop-sales-03", "laptop-exec-01",
]

# User accounts
USERS = [
    "john.doe", "jane.smith", "admin", "root", "service-account",
    "api-user", "backup-user", "monitoring", "developer1", "analyst2",
    "contractor-ext", "vendor-access", "guest-wifi", "temp-user",
]

# IP addresses
def generate_ip():
    """Generate realistic IP addresses"""
    internal_ranges = [
        (10, random.randint(0, 255), random.randint(0, 255), random.randint(1, 254)),  # 10.x.x.x
        (172, random.randint(16, 31), random.randint(0, 255), random.randint(1, 254)),  # 172.16-31.x.x
        (192, 168, random.randint(0, 255), random.randint(1, 254)),  # 192.168.x.x
    ]
    external_ranges = [
        (random.randint(1, 223), random.randint(0, 255), random.randint(0, 255), random.randint(1, 254)),
    ]
    
    # 70% internal, 30% external
    if random.random() < 0.7:
        ip = random.choice(internal_ranges)
    else:
        ip = random.choice(external_ranges)[0]
        ip = (ip[0], ip[1], ip[2], ip[3]) if isinstance(ip, tuple) else (ip, random.randint(0, 255), random.randint(0, 255), random.randint(1, 254))
    
    return f"{ip[0]}.{ip[1]}.{ip[2]}.{ip[3]}"

def generate_events(num_events: int = 500, hours_back: int = 24):
    """Generate realistic security events"""
    events = []
    now = datetime.now()
    
    # Calculate weights based on frequency
    weights = [p["frequency"] for p in SECURITY_PATTERNS]
    
    for i in range(num_events):
        # Select pattern based on frequency
        pattern = random.choices(SECURITY_PATTERNS, weights=weights)[0]
        
        # Generate timestamp (distributed over time window)
        time_offset = random.uniform(0, hours_back * 3600)
        timestamp = now - timedelta(seconds=time_offset)
        
        # Select host based on event category
        if pattern["category"] == "endpoint":
            host = random.choice([h for h in HOSTS if h.startswith("ws-") or h.startswith("laptop-")])
        elif pattern["category"] == "web":
            host = random.choice([h for h in HOSTS if h.startswith("web-")])
        elif pattern["category"] == "data":
            host = random.choice([h for h in HOSTS if h.startswith("db-")])
        elif pattern["category"] == "cloud":
            host = random.choice([h for h in HOSTS if h.startswith("ec2-") or h.startswith("aks-") or h.startswith("gke-")])
        else:
            host = random.choice(HOSTS)
        
        # Generate event ID
        event_id = hashlib.md5(f"{timestamp}{host}{pattern['signature']}".encode()).hexdigest()[:12]
        
        # Create event
        event = {
            "timestamp": timestamp.isoformat(),
            "event_id": event_id,
            "host": host,
            "entity_id": host.split(".")[0],  # Use hostname without domain
            "signature": pattern["signature"],
            "severity": pattern["severity"],
            "category": pattern["category"],
            "source": pattern["source"],
            "rule_id": f"RULE-{abs(hash(pattern['signature'])) % 1000:04d}",
            "source_ip": generate_ip(),
            "dest_ip": generate_ip(),
            "user": random.choice(USERS) if pattern["category"] == "authentication" else None,
            "count": 1,
            "_raw": f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} {host} {pattern['source']}: {pattern['signature']} detected from {generate_ip()}"
        }
        
        # Remove None values
        event = {k: v for k, v in event.items() if v is not None}
        
        # Add some duplicate events (30% chance)
        if random.random() < 0.3 and i > 0:
            # Duplicate a recent event with slight time modification
            base_event = events[max(0, i - random.randint(1, min(10, i)))]
            event = base_event.copy()
            event["timestamp"] = (datetime.fromisoformat(base_event["timestamp"]) + timedelta(seconds=random.randint(1, 60))).isoformat()
            event["count"] = base_event.get("count", 1) + 1
        
        events.append(event)
    
    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return events

def main():
    parser = argparse.ArgumentParser(description="Generate realistic security events")
    parser.add_argument("--num-events", type=int, default=500, help="Number of events to generate")
    parser.add_argument("--hours", type=int, default=24, help="Time window in hours")
    parser.add_argument("--output", default="data/raw/realistic_events.jsonl", help="Output file path")
    args = parser.parse_args()
    
    print(f"🔐 Generating {args.num_events} realistic security events...")
    events = generate_events(args.num_events, args.hours)
    
    # Write to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    
    # Statistics
    severity_counts = {}
    category_counts = {}
    duplicate_count = 0
    seen_signatures = set()
    
    for event in events:
        severity = event.get("severity", "unknown")
        category = event.get("category", "unknown")
        signature = f"{event.get('entity_id')}:{event.get('rule_id')}"
        
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
        
        if signature in seen_signatures:
            duplicate_count += 1
        seen_signatures.add(signature)
    
    print(f"✅ Generated {len(events)} events")
    print(f"📁 Saved to: {output_path}")
    print("\n📊 Statistics:")
    print(f"  Time range: {args.hours} hours")
    print(f"  Unique signatures: {len(seen_signatures)}")
    print(f"  Duplicate events: {duplicate_count} ({duplicate_count/len(events)*100:.1f}%)")
    print("\n  Severity distribution:")
    for sev, count in sorted(severity_counts.items()):
        print(f"    {sev}: {count} ({count/len(events)*100:.1f}%)")
    print("\n  Category distribution:")
    for cat, count in sorted(category_counts.items()):
        print(f"    {cat}: {count} ({count/len(events)*100:.1f}%)")

if __name__ == "__main__":
    main()
