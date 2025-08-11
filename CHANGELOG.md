# Changelog

## v0.2.0
- Helm chart 0.2.0: Ingress/HPA/PDB/NetworkPolicy/PVC/ServiceMonitor/PrometheusRule/Backup CronJob
- Non-root container image; health endpoints `/livez` `/readyz`
- Persistent audit logs (PVC) + optional S3 backup
- Secret-based API keys; Ingress auth/allowlist options
- Monitoring toggles; CI docker publish; immutable image tag usage

## v0.1.1
- Minor fixes and docs

## v0.1.0
- Initial MVP: core algorithms, FastAPI, SIEM connectors (Splunk/Sentinel/OpenSearch)
