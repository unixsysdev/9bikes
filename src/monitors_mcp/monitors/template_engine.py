"""
Monitor Template Engine - Helps guide users through monitor creation
"""
import re
from typing import Dict, List, Any, Optional
from .capabilities import MONITOR_CAPABILITIES

class MonitorTemplateEngine:
    """Helps Claude build the right monitor configuration through guided setup"""
    
    def infer_monitor_need(self, user_request: str) -> Dict[str, Any]:
        """Use keywords to guess what type of monitor they want"""
        request_lower = user_request.lower()
        
        suggestions = []
        confidence = 0.0
        
        # Crypto monitoring
        crypto_keywords = ['crypto', 'bitcoin', 'btc', 'ethereum', 'eth', 'trading', 'binance', 'coinbase']
        if any(word in request_lower for word in crypto_keywords):
            suggestions.append('crypto_trading')
            confidence = 0.8
        
        # GitHub monitoring
        github_keywords = ['github', 'git', 'repository', 'repo', 'commits', 'pull request', 'pr', 'issues']
        if any(word in request_lower for word in github_keywords):
            suggestions.append('github_events')
            confidence = max(confidence, 0.8)
        
        # Email monitoring
        email_keywords = ['email', 'gmail', 'inbox', 'mail', 'imap']
        if any(word in request_lower for word in email_keywords):
            suggestions.append('email_monitoring')
            confidence = max(confidence, 0.8)
        
        # API monitoring
        api_keywords = ['api', 'endpoint', 'rest', 'graphql', 'webhook', 'http']
        if any(word in request_lower for word in api_keywords):
            suggestions.append('api_monitoring')
            confidence = max(confidence, 0.7)
        
        # Website monitoring
        web_keywords = ['website', 'uptime', 'downtime', 'site', 'url', 'web page']
        if any(word in request_lower for word in web_keywords):
            suggestions.append('website_monitoring')
            confidence = max(confidence, 0.7)
        
        # Database monitoring
        db_keywords = ['database', 'mysql', 'postgres', 'sql', 'query', 'db']
        if any(word in request_lower for word in db_keywords):
            suggestions.append('database_monitoring')
            confidence = max(confidence, 0.7)
        
        # System monitoring
        system_keywords = ['server', 'cpu', 'memory', 'disk', 'system', 'performance']
        if any(word in request_lower for word in system_keywords):
            suggestions.append('system_monitoring')
            confidence = max(confidence, 0.7)
        
        if not suggestions:
            suggestions = ['api_monitoring']  # Default fallback
            confidence = 0.3
        
        return {
            "suggested_capabilities": suggestions,
            "confidence": confidence,
            "follow_up": self._generate_follow_up_question(suggestions[0] if suggestions else None)
        }
    
    def _generate_follow_up_question(self, capability: str) -> str:
        """Generate appropriate follow-up question based on capability"""
        questions = {
            "crypto_trading": "Which cryptocurrency exchange would you like to monitor? (Binance, Coinbase, etc.)",
            "github_events": "Would you like to receive webhooks for real-time updates, or poll the GitHub API periodically?",
            "email_monitoring": "Are you using Gmail with OAuth, or another email provider with IMAP?",
            "api_monitoring": "What's the API endpoint you'd like to monitor?",
            "website_monitoring": "Are you monitoring for uptime/downtime, or watching for content changes?",
            "database_monitoring": "Which database system? (MySQL, PostgreSQL, etc.)",
            "system_monitoring": "Do you want to monitor a remote server via SSH?"
        }
        return questions.get(capability, "What type of monitoring are you looking for?")
    
    def build_config_wizard(self, capability: str, provider: str) -> List[Dict[str, Any]]:
        """Generate step-by-step configuration questions"""
        if capability not in MONITOR_CAPABILITIES:
            raise ValueError(f"Unknown capability: {capability}")
        
        cap_info = MONITOR_CAPABILITIES[capability]
        if provider not in cap_info["providers"]:
            raise ValueError(f"Unknown provider: {provider}")
        
        provider_info = cap_info["providers"][provider]
        questions = []
        
        # Add setup questions from the provider
        if "setup_questions" in provider_info:
            questions.extend(provider_info["setup_questions"])
        
        # Add required secrets as questions
        for secret in provider_info.get("required_secrets", []):
            questions.append({
                "field": secret,
                "prompt": f"Please provide your {secret.replace('_', ' ')}",
                "type": "secret",
                "description": f"This will be stored securely and used for authentication"
            })
        
        # Add common fields
        questions.extend([
            {
                "field": "name",
                "prompt": "What should I call this monitor?",
                "type": "string",
                "example": f"My {provider.title()} Monitor"
            },
            {
                "field": "description",
                "prompt": "Brief description (optional)",
                "type": "string",
                "optional": True
            }
        ])
        
        return questions
    
    def validate_monitor_config(self, monitor_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate monitor configuration before deployment"""
        errors = []
        warnings = []
        
        # Find the template
        template = self._find_template_by_type(monitor_type)
        if not template:
            errors.append(f"Unknown monitor type: {monitor_type}")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check required fields
        required_fields = template.get("required_fields", [])
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate field formats
        validators = template.get("validators", {})
        for field, value in config.items():
            if field in validators:
                validator = validators[field]
                if callable(validator):
                    if not validator(value):
                        errors.append(f"Invalid format for {field}")
                elif isinstance(validator, str):  # Regex pattern
                    if not re.match(validator, str(value)):
                        errors.append(f"Invalid format for {field}: expected pattern {validator}")
        
        # Check for sensitive data in config
        sensitive_keywords = ['password', 'secret', 'key', 'token']
        for field, value in config.items():
            if any(keyword in field.lower() for keyword in sensitive_keywords):
                warnings.append(f"Field '{field}' contains sensitive data - consider using secrets instead")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _find_template_by_type(self, monitor_type: str) -> Optional[Dict[str, Any]]:
        """Find template configuration by monitor type"""
        for capability in MONITOR_CAPABILITIES.values():
            for provider in capability["providers"].values():
                if provider.get("monitor_type") == monitor_type:
                    return provider
        return None
    
    def generate_kubernetes_config(self, monitor_id: str, monitor_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Kubernetes deployment configuration"""
        
        monitor_type = monitor_config.get("monitor_type", "generic")
        
        # Base deployment configuration
        deployment_config = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"monitor-{monitor_id}",
                "labels": {
                    "app": "monitor",
                    "monitor_id": monitor_id,
                    "user_id": monitor_config.get("user_id"),
                    "monitor_type": monitor_type
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "monitor_id": monitor_id
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "monitor_id": monitor_id,
                            "app": "monitor"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "monitor",
                            "image": f"monitors/{monitor_type}:latest",
                            "env": [
                                {"name": "MONITOR_ID", "value": monitor_id},
                                {"name": "CONFIG", "value": str(monitor_config)},
                                {"name": "INFLUX_URL", "value": "http://influxdb:8086"},
                                {
                                    "name": "INFLUX_TOKEN",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": f"monitor-{monitor_id}-secrets",
                                            "key": "influx_token"
                                        }
                                    }
                                }
                            ],
                            "resources": {
                                "limits": {
                                    "memory": "128Mi",
                                    "cpu": "100m"
                                },
                                "requests": {
                                    "memory": "64Mi",
                                    "cpu": "50m"
                                }
                            },
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": 8080
                                },
                                "initialDelaySeconds": 10,
                                "periodSeconds": 30
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/ready",
                                    "port": 8080
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 10
                            }
                        }]
                    }
                }
            }
        }
        
        return deployment_config
    
    def suggest_alert_rules(self, monitor_type: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest default alert rules based on monitor type"""
        
        suggestions = []
        
        if monitor_type == "api_poller":
            suggestions.extend([
                {
                    "title": "API Endpoint Down",
                    "condition": {
                        "type": "threshold",
                        "field": "status_code",
                        "operator": ">=",
                        "value": 400
                    },
                    "severity": "high",
                    "description": "Alert when API returns error status codes"
                },
                {
                    "title": "Slow Response Time",
                    "condition": {
                        "type": "threshold",
                        "field": "response_time",
                        "operator": ">",
                        "value": 5.0
                    },
                    "severity": "medium",
                    "description": "Alert when response time exceeds 5 seconds"
                }
            ])
        
        elif monitor_type == "websocket_stream":
            suggestions.extend([
                {
                    "title": "WebSocket Disconnected",
                    "condition": {
                        "type": "absence",
                        "field": "message_count",
                        "duration": "5m"
                    },
                    "severity": "high",
                    "description": "Alert when no messages received for 5 minutes"
                }
            ])
        
        elif monitor_type == "crypto_ws_monitor":
            suggestions.extend([
                {
                    "title": "Price Spike Alert",
                    "condition": {
                        "type": "change_percent",
                        "field": "price",
                        "operator": ">",
                        "value": 5.0,
                        "timeframe": "1h"
                    },
                    "severity": "medium",
                    "description": "Alert on significant price movements"
                }
            ])
        
        elif monitor_type == "uptime_monitor":
            suggestions.extend([
                {
                    "title": "Website Down",
                    "condition": {
                        "type": "threshold",
                        "field": "status_code",
                        "operator": "!=",
                        "value": 200
                    },
                    "severity": "critical",
                    "description": "Alert when website is not responding with 200 OK"
                }
            ])
        
        return suggestions
