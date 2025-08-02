"""
Monitor Deployment Manager - Handles Kubernetes deployments for monitors
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

class MonitorDeploymentManager:
    """Manages monitor deployments in Kubernetes"""
    
    def __init__(self):
        self.k8s_apps_v1 = None
        self.k8s_core_v1 = None
        self.namespace = "monitors"
        self._initialize_k8s_client()
    
    def _initialize_k8s_client(self):
        """Initialize Kubernetes client"""
        try:
            # Try in-cluster config first (when running in K8s)
            config.load_incluster_config()
            logger.info("Using in-cluster Kubernetes config")
        except:
            try:
                # Fall back to local kubeconfig
                config.load_kube_config()
                logger.info("Using local kubeconfig")
            except Exception as e:
                logger.warning(f"Failed to load Kubernetes config: {e}")
                logger.warning("Monitor deployment will be simulated")
                return
        
        self.k8s_apps_v1 = client.AppsV1Api()
        self.k8s_core_v1 = client.CoreV1Api()
    
    async def deploy_monitor(self, monitor_id: str, monitor_config: Dict[str, Any], 
                           secrets: Dict[str, str] = None) -> Dict[str, Any]:
        """Deploy a monitor to Kubernetes"""
        try:
            if not self.k8s_apps_v1:
                return await self._simulate_deployment(monitor_id, monitor_config)
            
            # Create namespace if it doesn't exist
            await self._ensure_namespace()
            
            # Create secrets
            if secrets:
                await self._create_secrets(monitor_id, secrets)
            
            # Generate deployment config
            from .template_engine import MonitorTemplateEngine
            template_engine = MonitorTemplateEngine()
            deployment_config = template_engine.generate_kubernetes_config(monitor_id, monitor_config)
            
            # Deploy to Kubernetes
            deployment_name = f"monitor-{monitor_id}"
            
            try:
                # Check if deployment already exists
                self.k8s_apps_v1.read_namespaced_deployment(
                    name=deployment_name, 
                    namespace=self.namespace
                )
                
                # Update existing deployment
                self.k8s_apps_v1.patch_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.namespace,
                    body=deployment_config
                )
                logger.info(f"Updated Kubernetes deployment: {deployment_name}")
                
            except ApiException as e:
                if e.status == 404:
                    # Create new deployment
                    self.k8s_apps_v1.create_namespaced_deployment(
                        namespace=self.namespace,
                        body=deployment_config
                    )
                    logger.info(f"Created Kubernetes deployment: {deployment_name}")
                else:
                    raise
            
            return {
                "deployment_id": deployment_name,
                "status": "deployed",
                "namespace": self.namespace
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy monitor {monitor_id}: {e}")
            return {
                "deployment_id": None,
                "status": "failed",
                "error": str(e)
            }
    
    async def _simulate_deployment(self, monitor_id: str, monitor_config: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate deployment when K8s is not available"""
        logger.info(f"SIMULATING deployment for monitor {monitor_id}")
        logger.info(f"Config: {json.dumps(monitor_config, indent=2)}")
        
        # Simulate deployment delay
        await asyncio.sleep(1)
        
        deployment_name = f"monitor-{monitor_id}-simulated"
        return {
            "deployment_id": deployment_name,
            "status": "deployed_simulated",
            "namespace": "simulated"
        }
    
    async def _ensure_namespace(self):
        """Ensure the monitors namespace exists"""
        try:
            self.k8s_core_v1.read_namespace(self.namespace)
        except ApiException as e:
            if e.status == 404:
                # Create namespace
                namespace_body = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=self.namespace)
                )
                self.k8s_core_v1.create_namespace(body=namespace_body)
                logger.info(f"Created namespace: {self.namespace}")
    
    async def _create_secrets(self, monitor_id: str, secrets: Dict[str, str]):
        """Create Kubernetes secrets for the monitor"""
        secret_name = f"monitor-{monitor_id}-secrets"
        
        try:
            # Create secret
            secret_body = client.V1Secret(
                metadata=client.V1ObjectMeta(name=secret_name),
                string_data=secrets
            )
            
            try:
                # Try to update existing secret
                self.k8s_core_v1.patch_namespaced_secret(
                    name=secret_name,
                    namespace=self.namespace,
                    body=secret_body
                )
            except ApiException as e:
                if e.status == 404:
                    # Create new secret
                    self.k8s_core_v1.create_namespaced_secret(
                        namespace=self.namespace,
                        body=secret_body
                    )
            
            logger.info(f"Created/updated secrets for monitor {monitor_id}")
            
        except Exception as e:
            logger.error(f"Failed to create secrets for monitor {monitor_id}: {e}")
            raise
    
    async def stop_monitor(self, deployment_id: str) -> bool:
        """Stop a monitor deployment"""
        try:
            if not self.k8s_apps_v1:
                logger.info(f"SIMULATING stop for deployment {deployment_id}")
                return True
            
            # Delete deployment
            self.k8s_apps_v1.delete_namespaced_deployment(
                name=deployment_id,
                namespace=self.namespace
            )
            
            # Delete associated secrets
            secret_name = deployment_id.replace("monitor-", "monitor-") + "-secrets"
            try:
                self.k8s_core_v1.delete_namespaced_secret(
                    name=secret_name,
                    namespace=self.namespace
                )
            except ApiException:
                pass  # Secret might not exist
            
            logger.info(f"Stopped monitor deployment: {deployment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop monitor {deployment_id}: {e}")
            return False
    
    async def get_monitor_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get the status of a monitor deployment"""
        try:
            if not self.k8s_apps_v1:
                return {
                    "status": "simulated",
                    "ready_replicas": 1,
                    "total_replicas": 1
                }
            
            deployment = self.k8s_apps_v1.read_namespaced_deployment(
                name=deployment_id,
                namespace=self.namespace
            )
            
            status = deployment.status
            return {
                "status": "running" if status.ready_replicas == status.replicas else "starting",
                "ready_replicas": status.ready_replicas or 0,
                "total_replicas": status.replicas or 0,
                "conditions": [
                    {
                        "type": condition.type,
                        "status": condition.status,
                        "reason": condition.reason
                    }
                    for condition in (status.conditions or [])
                ]
            }
            
        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found"}
            raise
        except Exception as e:
            logger.error(f"Failed to get status for {deployment_id}: {e}")
            return {"status": "error", "error": str(e)}

# Global deployment manager instance
deployment_manager = MonitorDeploymentManager()
