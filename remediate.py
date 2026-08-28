#!/usr/bin/env python3
import sys
import subprocess
import datetime
import argparse

subprocess.run([sys.executable, "-m", "pip", "install", "kubernetes", "-q"], check=True)

from kubernetes import client, config

parser = argparse.ArgumentParser()
parser.add_argument("--deployment", required=True)
parser.add_argument("--namespace", default="easytrade")
args = parser.parse_args()

try:
    config.load_kube_config()
except Exception:
    config.load_incluster_config()

apps = client.AppsV1Api()
patch = {
    "spec": {
        "template": {
            "metadata": {
                "annotations": {
                    "kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow().isoformat() + "Z"
                }
            }
        }
    }
}
apps.patch_namespaced_deployment(args.deployment, args.namespace, patch)
print(f"Restart triggered for {args.deployment} in {args.namespace}")

import time
for i in range(24):
    d = apps.read_namespaced_deployment(args.deployment, args.namespace)
    desired = d.spec.replicas or 1
    ready = d.status.ready_replicas or 0
    updated = d.status.updated_replicas or 0
    print(f"Attempt {i+1}: desired={desired} updated={updated} ready={ready}")
    if updated == desired and ready == desired:
        print("Rollout complete")
        sys.exit(0)
    time.sleep(5)

print("Timeout waiting for rollout")
sys.exit(1)