#!/usr/bin/env python3
import sys
import subprocess
import datetime
import argparse
import os
import time

subprocess.run([sys.executable, "-m", "pip", "install", "kubernetes", "-q"], check=True)

from kubernetes import client

parser = argparse.ArgumentParser()
parser.add_argument("--deployment", required=True)
parser.add_argument("--namespace", default="easytrade")
args = parser.parse_args()

# AWX injects Kubernetes credentials as environment variables
host = os.environ.get("K8S_AUTH_HOST")
api_key = os.environ.get("K8S_AUTH_API_KEY")
verify_ssl = os.environ.get("K8S_AUTH_VERIFY_SSL", "true").lower() != "false"
ssl_ca_cert = os.environ.get("K8S_AUTH_SSL_CA_CERT")  # path to CA cert file if set

if not host or not api_key:
    print(f"ERROR: K8S_AUTH_HOST={host}, K8S_AUTH_API_KEY={'set' if api_key else 'MISSING'}")
    sys.exit(1)

configuration = client.Configuration()
configuration.host = host
configuration.api_key = {"authorization": f"Bearer {api_key}"}
configuration.verify_ssl = verify_ssl
if ssl_ca_cert:
    configuration.ssl_ca_cert = ssl_ca_cert

with client.ApiClient(configuration) as api_client:
    apps = client.AppsV1Api(api_client)

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