#!/usr/bin/env bash
set -e
# One-liner EKS deploy for edge-fleet-control-loop
# Assumes: aws cli + kubectl + eksctl installed and `aws sso login` or creds done
# Usage: ./scripts/deploy_eks_one_liner.sh [cluster-name] [region]
CLUSTER=${1:-edge-fleet-test}
REGION=${2:-us-west-2}

echo "== $CLUSTER @ $REGION =="

# 1. create if missing
if ! eksctl get cluster --region $REGION --name $CLUSTER 2>/dev/null | grep -q $CLUSTER; then
  echo "Creating EKS $CLUSTER (managed spot 2×t3.medium, 2-4 scale)..."
  eksctl create cluster \
    --name $CLUSTER --region $REGION \
    --node-type t3.medium --nodes 2 --nodes-min 2 --nodes-max 4 \
    --managed --spot --asg-access
fi

aws eks update-kubeconfig --region $REGION --name $CLUSTER

# 2. deploy manifests
kubectl apply -k k8s/

# 3. wait + show HPA
kubectl wait --for=condition=available deploy/control-plane --timeout=120s || true
kubectl get pods -l app=control-plane
kubectl get hpa -o wide || echo "HPA waiting on metrics-server (need metrics-server installed: kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml )"

# 4. port-forward hint + scale test against EKS LB (replace URL after svc)
echo ""
echo "Test (once LB ready):"
echo "  kubectl port-forward svc/control-plane 8000:8000 &"
echo "  python3 scale_test/harness.py --devices 500 --qps 0.2 --control http://localhost:8000"
echo ""
echo "Debug storm isolation test:"
echo "  for i in seq 10; do curl -X POST http://localhost:8000/api/v1/debug -H 'Content-Type: application/json' -d \"{\\\"device_id\\\":\\\"storm_01\\\",\\\"fw_version\\\":\\\"v_bad\\\",\\\"level\\\":\\\"panic\\\",\\\"signature\\\":\\\"crash @ \\$i\\\"}\" ; done"
echo ""
echo "Teardown when done:"
echo "  eksctl delete cluster --name $CLUSTER --region $REGION --wait"
