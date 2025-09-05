#!/usr/bin/env python3
"""
Test connection to local Splunk Enterprise instance
"""
import requests
import json
import urllib3
from datetime import datetime, timedelta

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Splunk Enterprise credentials
SPLUNK_HOST = "192.168.1.12"
SPLUNK_PORT = 8089
USERNAME = "ceo@ruuley.com"
PASSWORD = "znGsViXLMJZpq!oQ.-pEe-7qqsYqc"

def get_session_key():
    """Get session key from Splunk"""
    url = f"http://{SPLUNK_HOST}:{SPLUNK_PORT}/services/auth/login"
    data = {
        'username': USERNAME,
        'password': PASSWORD,
        'output_mode': 'json'
    }
    
    try:
        response = requests.post(url, data=data, verify=False)
        if response.status_code == 200:
            session_key = response.json()['sessionKey']
            print(f"✅ Successfully authenticated to Splunk Enterprise")
            print(f"📍 Host: {SPLUNK_HOST}:{SPLUNK_PORT}")
            print(f"🔑 Session Key: {session_key[:20]}...")
            return session_key
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def search_events(session_key, search_query="search index=* | head 10"):
    """Execute search query on Splunk"""
    headers = {
        'Authorization': f'Splunk {session_key}'
    }
    
    # Create search job
    job_url = f"http://{SPLUNK_HOST}:{SPLUNK_PORT}/services/search/jobs"
    job_data = {
        'search': search_query,
        'output_mode': 'json',
        'exec_mode': 'oneshot',  # Execute immediately
        'earliest_time': '-24h@h',
        'latest_time': 'now'
    }
    
    try:
        print(f"\n🔍 Executing search: {search_query}")
        response = requests.post(job_url, headers=headers, data=job_data, verify=False)
        
        if response.status_code == 200:
            results = response.json()
            if 'results' in results:
                print(f"✅ Found {len(results['results'])} events")
                return results['results']
            else:
                print("⚠️ No results found")
                return []
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(response.text[:500])
            return []
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []

def fetch_security_events(session_key):
    """Fetch security-related events from Splunk"""
    # Common security searches for Splunk Enterprise
    searches = [
        # Splunk internal events (より多くのイベントを取得)
        "search index=_internal | head 500",
        "search index=_audit | head 200",
        
        # Windows Security Events
        "search index=main OR index=wineventlog | head 200",
        
        # All events with errors/warnings
        "search index=* (ERROR OR WARN OR failed OR error OR denied OR blocked) | head 300",
        
        # Any events (fallback)
        "search index=* | head 1000"
    ]
    
    all_events = []
    for search in searches:
        events = search_events(session_key, search)
        if events:
            all_events.extend(events)
            print(f"  → Collected {len(events)} events")
            
            # Show sample event
            if events and len(events) > 0:
                sample = events[0]
                print(f"  Sample: {sample.get('_raw', str(sample))[:100]}...")
        
        if len(all_events) >= 500:
            break
    
    return all_events

def save_events(events, output_file="data/raw/splunk_local_events.jsonl"):
    """Save events to JSONL file"""
    from pathlib import Path
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert Splunk events to our format
    converted_events = []
    for event in events:
        converted = {
            "timestamp": event.get('_time', datetime.now().isoformat()),
            "host": event.get('host', 'unknown'),
            "source": event.get('source', 'unknown'),
            "sourcetype": event.get('sourcetype', 'unknown'),
            "entity_id": event.get('host', 'unknown'),
            "rule_id": f"RULE-{abs(hash(event.get('_raw', ''))) % 10000:04d}",
            "_raw": event.get('_raw', str(event)),
        }
        
        # Try to determine severity
        raw_lower = converted['_raw'].lower()
        if any(word in raw_lower for word in ['critical', 'fatal', 'emergency']):
            converted['severity'] = 'critical'
        elif any(word in raw_lower for word in ['error', 'failed', 'denied', 'blocked']):
            converted['severity'] = 'high'
        elif any(word in raw_lower for word in ['warning', 'warn']):
            converted['severity'] = 'medium'
        else:
            converted['severity'] = 'low'
        
        # Try to determine signature
        if 'EventCode=4625' in converted['_raw']:
            converted['signature'] = 'Failed_Login_Attempt'
        elif 'EventCode=4624' in converted['_raw']:
            converted['signature'] = 'Successful_Login'
        elif 'error' in raw_lower:
            converted['signature'] = 'Error_Event'
        elif 'failed' in raw_lower:
            converted['signature'] = 'Failed_Operation'
        else:
            converted['signature'] = 'General_Event'
        
        converted_events.append(converted)
    
    with open(output_path, 'w') as f:
        for event in converted_events:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    
    print(f"\n💾 Saved {len(converted_events)} events to {output_path}")
    return output_path

def main():
    print("🚀 Connecting to local Splunk Enterprise...")
    print("="*50)
    
    # Get session key
    session_key = get_session_key()
    if not session_key:
        print("\n❌ Failed to connect to Splunk Enterprise")
        print("確認事項:")
        print("1. Splunkd サービスが起動しているか")
        print("2. ポート 8089 が開いているか")
        print("3. 認証情報が正しいか")
        return
    
    # Fetch events
    print("\n📥 Fetching security events from Splunk...")
    events = fetch_security_events(session_key)
    
    if events:
        print(f"\n✅ Successfully fetched {len(events)} events from Splunk Enterprise")
        
        # Save events
        output_file = save_events(events)
        
        # Show statistics
        print("\n📊 Event Statistics:")
        print(f"  Total events: {len(events)}")
        
        # Count by sourcetype
        sourcetypes = {}
        for event in events:
            st = event.get('sourcetype', 'unknown')
            sourcetypes[st] = sourcetypes.get(st, 0) + 1
        
        print("\n  Events by sourcetype:")
        for st, count in sorted(sourcetypes.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {st}: {count}")
        
        print(f"\n🎯 Next step: Run A/B testing with real Splunk data")
        print(f"   python scripts/ab/ab_split.py --in {output_file} --out-dir data/ab_split_splunk --salt 2025")
    else:
        print("\n⚠️ No events found. Check if Splunk has data.")

if __name__ == "__main__":
    main()
