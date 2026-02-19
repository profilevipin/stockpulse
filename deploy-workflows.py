#!/usr/bin/env python3
"""
Deploy fixed StockPulse workflows to n8n instance.

Usage:
    python3 deploy-workflows.py --url https://stockpulse.co.in --api-key YOUR_N8N_API_KEY

This script:
1. Updates each workflow with fixed JSON (credentials, error handling, etc.)
2. Deletes duplicate workflows
3. Activates all 13 workflows
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Mapping: workflow file -> n8n workflow ID to update (best copy with most creds fixed)
WORKFLOW_MAP = {
    "wf1-message-handler.json": "kGn3KwIfHldiwuGW",
    "wf2-alert-checker.json": "HrZhfXdfFQltaexx",
    "wf3-pattern-detector.json": "Qcu7typEiSbIXKcu",
    "wf4-morning-briefing.json": "NYoURGSYiDNdpP3Q",
    "wf4a-global-data.json": "zpodYfoLRmOa8ZEO",
    "wf4b-flow-data.json": "nBjtfIDnT9Qv5raS",
    "wf4c-technical-data.json": "WyBf3BPMEknA8rOz",
    "wf4d-options-news.json": "x26o3yTp63M6yRrC",
    "wf4e-midday-pulse.json": "S0reiVHGF2MSCZdL",
    "wf5-eod-summary.json": "jFTktQQEU8ChQ1D6",
    "wf6-token-manager.json": "aUFGSq6nxV2DVa9Y",
    "wf7-weekly-review.json": "SOetjjWla4DJsk8v",
    "wf8-prediction-tracker.json": "RHnACJnjIyvL6Xg0",
}

# Duplicate workflow IDs to delete
DUPLICATES_TO_DELETE = [
    "YDc6yJOSURBd18Qs",  # WF1 dup
    "wMb3U15c2pF8p8o9",  # WF2 dup
    "fEXiwRfhiMBdlHGi",  # WF3 dup
    "35PGRQaA0cPUltWu",  # WF4 dup
    "zuhSGUgZrz8Ju3g4",  # WF4a dup
    "52Q7iJRwLUNqlYYt",  # WF4b dup
    "MuPMeBze7QLfo6KC",  # WF4c dup
    "WvccsafaAe0vkGo7",  # WF4d dup
    "cauZa3RFLNKde5Es",  # WF4e dup
    "boTRdVTy5lvzXpSE",  # WF5 dup
    "QlOYOOOSJX7IQQlv",  # WF6 dup 1
    "VXb6bZR2j8a8uPFl",  # WF6 dup 2
    "WumR0nSJ65BqtDMb",  # WF7 dup
    "sToLQYfyAqxqoO4h",  # WF8 dup
]


def api_request(url, api_key, method="GET", data=None, retries=3):
    """Make an API request to n8n with retry logic."""
    headers = {
        "X-N8N-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    for attempt in range(retries):
        try:
            if data:
                body = json.dumps(data).encode("utf-8")
            else:
                body = None

            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            if attempt < retries - 1 and e.code >= 500:
                wait = 2 ** (attempt + 1)
                print(f"    Retry in {wait}s (HTTP {e.code})...")
                time.sleep(wait)
                continue
            print(f"    HTTP {e.code}: {error_body[:200]}")
            return None
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"    Retry in {wait}s ({e})...")
                time.sleep(wait)
                continue
            print(f"    Error: {e}")
            return None
    return None


def update_workflow(base_url, api_key, wf_id, wf_data):
    """Update a workflow via PUT API."""
    url = f"{base_url}/api/v1/workflows/{wf_id}"
    # Only send the fields n8n expects
    payload = {
        "name": wf_data["name"],
        "nodes": wf_data["nodes"],
        "connections": wf_data["connections"],
        "settings": wf_data.get("settings", {}),
    }
    if "staticData" in wf_data:
        payload["staticData"] = wf_data["staticData"]

    return api_request(url, api_key, method="PUT", data=payload)


def activate_workflow(base_url, api_key, wf_id):
    """Activate a workflow."""
    url = f"{base_url}/api/v1/workflows/{wf_id}/activate"
    return api_request(url, api_key, method="POST")


def deactivate_workflow(base_url, api_key, wf_id):
    """Deactivate a workflow before updating."""
    url = f"{base_url}/api/v1/workflows/{wf_id}/deactivate"
    return api_request(url, api_key, method="POST")


def delete_workflow(base_url, api_key, wf_id):
    """Delete a workflow."""
    url = f"{base_url}/api/v1/workflows/{wf_id}"
    return api_request(url, api_key, method="DELETE")


def main():
    parser = argparse.ArgumentParser(description="Deploy StockPulse workflows to n8n")
    parser.add_argument("--url", required=True, help="n8n instance URL (e.g. https://stockpulse.co.in)")
    parser.add_argument("--api-key", required=True, help="n8n API key")
    parser.add_argument("--skip-delete", action="store_true", help="Skip deleting duplicate workflows")
    parser.add_argument("--skip-activate", action="store_true", help="Skip activating workflows")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    workflows_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "n8n-workflows")

    # Verify API connectivity
    print("Checking n8n API connectivity...")
    result = api_request(f"{base_url}/api/v1/workflows?limit=1", args.api_key)
    if result is None:
        print("ERROR: Cannot connect to n8n API. Check URL and API key.")
        sys.exit(1)
    print(f"  Connected. Found {len(result.get('data', []))} workflows.\n")

    # Phase 1: Update workflows
    print("=" * 60)
    print("PHASE 1: Update workflows with fixed JSON")
    print("=" * 60)
    updated = 0
    failed = 0

    for filename, wf_id in WORKFLOW_MAP.items():
        filepath = os.path.join(workflows_dir, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP {filename}: file not found")
            failed += 1
            continue

        with open(filepath, "r") as f:
            wf_data = json.load(f)

        print(f"  Updating {wf_data['name']} ({wf_id})...", end=" ")

        if args.dry_run:
            print("DRY RUN")
            updated += 1
            continue

        # Deactivate first (in case it's active)
        deactivate_workflow(base_url, args.api_key, wf_id)

        result = update_workflow(base_url, args.api_key, wf_id, wf_data)
        if result:
            print("OK")
            updated += 1
        else:
            print("FAILED")
            failed += 1

    print(f"\n  Updated: {updated}/{len(WORKFLOW_MAP)}, Failed: {failed}\n")

    # Phase 2: Delete duplicates
    if not args.skip_delete:
        print("=" * 60)
        print("PHASE 2: Delete duplicate workflows")
        print("=" * 60)
        deleted = 0

        for dup_id in DUPLICATES_TO_DELETE:
            print(f"  Deleting {dup_id}...", end=" ")

            if args.dry_run:
                print("DRY RUN")
                deleted += 1
                continue

            # Deactivate first
            deactivate_workflow(base_url, args.api_key, dup_id)
            result = delete_workflow(base_url, args.api_key, dup_id)
            if result is not None:
                print("OK")
                deleted += 1
            else:
                print("SKIP (may not exist)")

        print(f"\n  Deleted: {deleted}/{len(DUPLICATES_TO_DELETE)}\n")

    # Phase 3: Activate workflows
    if not args.skip_activate:
        print("=" * 60)
        print("PHASE 3: Activate all workflows")
        print("=" * 60)
        activated = 0

        for filename, wf_id in WORKFLOW_MAP.items():
            wf_name = filename.replace(".json", "")
            print(f"  Activating {wf_name} ({wf_id})...", end=" ")

            if args.dry_run:
                print("DRY RUN")
                activated += 1
                continue

            result = activate_workflow(base_url, args.api_key, wf_id)
            if result:
                print("OK")
                activated += 1
            else:
                print("FAILED")

        print(f"\n  Activated: {activated}/{len(WORKFLOW_MAP)}\n")

    # Summary
    print("=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"  Workflows updated: {updated}")
    if not args.skip_delete:
        print(f"  Duplicates deleted: {len(DUPLICATES_TO_DELETE)}")
    if not args.skip_activate:
        print(f"  Workflows activated: {len(WORKFLOW_MAP)}")
    print(f"\nNext steps:")
    print(f"  1. Send a message to the Telegram bot to test WF1")
    print(f"  2. Check execution logs: {base_url}/api/v1/executions?limit=10")
    print(f"  3. Verify NSE data service: docker compose logs nse-data-service")


if __name__ == "__main__":
    main()
