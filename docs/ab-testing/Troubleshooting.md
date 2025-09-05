# AB Troubleshooting

- Metrics all zeros
  - Check /reports has `ab_YYYY-MM-DD.json` and API shares the same PVC.
- A/B counts very imbalanced
  - Verify key fields for assignment. Consider different `--salt` before start.
- Slack notify fails
  - Ensure webhook secret present and file exists in /reports.
- Cron runs but no data
  - Validate SIEM credentials, endpoint reachability, and certs.
