# Cost Estimate — Real EKS Test (Option 2)

You asked what it would cost to run the K8s integration for real on AWS.

## Short answer: <$1 for a quick 2-hour spin, ~$13 if you leave it 3 days.

| Item | Unit price (us-west-2) | Notes |
|------|------------------------|-------|
| EKS control plane | $0.10/hr | AWS managed, 1 cluster |
| EC2 t3.medium (2 vCPU 4GB) ×2 | $0.0416/hr each = $0.0832/hr | Runs control-plane (2 pods) + log-processor (3) + debug-processor (2) + HPA |
| Total 2-node cluster | $0.1832/hr | $4.40/day |
| Bigger test (2× t3.large or 3× medium) | $0.266/hr | $6.39/day |
| Spot (same, 70% off nodes) | ~$0.08/hr total | ~$1.92/day |
| ECR storage / transfer | < $0.50 total | 3 images ~200MB each |
| Data transfer (if outside) | $0.09/GB | negligible for telemetry test |

**Cost-cut playbook:**

```bash
# create (spot = cheapest)
eksctl create cluster \
  --name edge-fleet-test --region us-west-2 \
  --node-type t3.medium --nodes 2 --nodes-min 2 --nodes-max 4 \
  --managed --spot

# test 90 min then kill
eksctl delete cluster --name edge-fleet-test --region us-west-2 --wait
# Total ~0.55 hr × $0.08 (spot) = $0.22 + EKS $0.10 = $0.32
```

**What a 3-day linger costs:**
- On-demand 2× medium: 72hr × $0.1832 = $13.19
- Spot: 72hr × $0.08 = ~$5.76

Leaves: no recurring cost after delete — EKS + EC2 gone.

Recommended: run on spot for first go, keep t3.medium, kill after.
