NS ?= bolcd
RELEASE ?= bolcd
IMAGE_TAG ?=
INGRESS_ENABLED ?= false

.PHONY: preflight deploy postflight ab-run-once metrics port-forward ab-demo ab-report ab-weekly kpi-daily kpi-test

preflight:
	@bash scripts/k8s-preflight.sh $(NS) --release $(RELEASE) || true

deploy:
	@if [ -n "$(IMAGE_TAG)" ]; then \
		helm upgrade --install $(RELEASE) ./deploy/helm -n $(NS) -f deploy/helm/values-prod.yaml \
		  --set ingress.enabled=$(INGRESS_ENABLED) --set image.tag=$(IMAGE_TAG) \
		  --create-namespace --wait --timeout 10m; \
	else \
		helm upgrade --install $(RELEASE) ./deploy/helm -n $(NS) -f deploy/helm/values-prod.yaml \
		  --set ingress.enabled=$(INGRESS_ENABLED) \
		  --create-namespace --wait --timeout 10m; \
	fi

postflight:
	@bash scripts/k8s-preflight.sh $(NS) --release $(RELEASE) --check-post || true

ab-run-once:
	@kubectl -n $(NS) create job --from=cronjob/$(RELEASE)-ab-daily ab-manual-`date +%s`

metrics:
	@set -e; \
	kubectl -n $(NS) port-forward svc/$(RELEASE) 8080:8080 >/dev/null 2>&1 & echo $$! > .pfpid; \
	sleep 2; \
	if [ ! -s .pfpid ] || ! kill -0 `cat .pfpid` 2>/dev/null; then echo "port-forward failed" >&2; rm -f .pfpid; exit 1; fi; \
	curl -s localhost:8080/metrics | grep ^bolcd_ab_ || true; \
	kill `cat .pfpid` 2>/dev/null || true; rm -f .pfpid

port-forward:
	@kubectl -n $(NS) port-forward svc/$(RELEASE) 8080:8080


ab-demo:
	python scripts/ab/ab_split.py --in data/sample/events.jsonl --out-dir /tmp/ab

ab-report:
	python scripts/ab/ab_report.py --in-a /tmp/ab/A.jsonl --in-b /tmp/ab/B.jsonl --out-dir /reports --date-label $$\(date -u +"%Y-%m-%d"\)

ab-weekly:
	python scripts/ab/ab_weekly.py --dir /reports --out /reports/weekly.json

kpi-daily:
	python scripts/kpi/compute_kpi.py --reports-dir /reports --date $$(date -u +"%Y-%m-%d") \
		--ingest-a-gb $${INGEST_A_GB:-} --ingest-b-gb $${INGEST_B_GB:-} --cost-per-gb-usd $${COST_PER_GB_USD:-}

kpi-test:
	pytest -q tests/kpi/test_kpi_pipeline.py

