# SQL / KQL Examples

## Splunk (SPL)
```
index=security earliest=-24h latest=now
| fields _time, rule_id, entity_id, severity, source, sourcetype
```

## Sentinel (KQL)
```
SecurityEvent
| where TimeGenerated between (ago(24h) .. now())
| project TimeGenerated, rule_id, entity_id, Severity, Source
```

## OpenSearch (SQL)
```
SELECT @timestamp, rule_id, entity_id, severity, source
FROM security
WHERE @timestamp BETWEEN now() - INTERVAL 1 DAY AND now()
LIMIT 100000;
```
