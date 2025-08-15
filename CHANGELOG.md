# Changelog

## v0.2.1
- Helm: weekly CronJob supports `--keys`; new `ab-notify` CronJob to post daily A/B MD to webhook
- Reports: weekly MD table rendering fixed when no rows; added no-data message
- Version bump to 0.2.1 (API/Chart/pyproject); docs updated

## v0.2.2
- API: expose latest daily AB as metrics (`bolcd_ab_*`) and added endpoints to fetch daily reports JSON
- Helm: mount `/reports` PVC in Deployment; add alerts for AB reduction drop, regressions spike (unique/count), and stale reports
- Reports: effects include `new_in_b_unique` and `new_in_b_count` for accurate metrics
- Version bump to 0.2.2

## v1.0.0

- Production-ready release: security hardening (HTTPS/HSTS, app headers, rate limiting), OIDC-ready, Vault + ExternalSecrets v1, Helm chart (Ingress/HPA/PDB/NetworkPolicy/ServiceMonitor/PrometheusRule/Grafana), CI (lint/test, schema fuzz, helm lint+kubeconform), Docker image signing (cosign) & SBOM (syft), AlertmanagerConfig templated
- Chart and app versions aligned to 1.0.0

## v0.2.3
- Helm: Service labeled with `app: bolcd` for ServiceMonitor selector; ServiceMonitor uses `jobLabel: app`
- Alerts: p95 latency query switched to `bolcd_http_request_duration_seconds_bucket`; HTTP 4xx/5xx alert queries validated
- Grafana: optional dashboard ConfigMap with latency/error-rate/AB panels (`monitor.grafana.enabled`)
- Docs: README notes for enabling ServiceMonitor, alerts, and Grafana dashboard
- Alerts: optional HTTP 429 error-rate alert and rate-limit spike alert (`monitor.alerts.http.errorRate429`, `monitor.alerts.rateLimit.*`)
- Chart version bump to 0.2.3; app/library version aligned to 0.2.3

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
