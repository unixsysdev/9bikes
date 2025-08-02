#!/bin/bash
# Build and deploy alert engine

set -e

echo "🔨 Building Alert Engine Docker Image..."

# Build Docker image
docker build -f docker/alert-engine.Dockerfile -t monitors/alert-engine:latest .

echo "✅ Alert Engine image built successfully"

# Check if we should deploy to Kubernetes
if [ "$1" = "deploy" ]; then
    echo "🚀 Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace monitors --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s/alert-engine-deployment.yaml
    
    echo "✅ Alert Engine deployed to Kubernetes"
    echo "📊 Check status with: kubectl get pods -n monitors"
    echo "📋 View logs with: kubectl logs -n monitors -l app=alert-engine"
else
    echo "💡 To deploy to Kubernetes, run: $0 deploy"
    echo "🏃 To run locally: docker run -d --name alert-engine monitors/alert-engine:latest"
fi
