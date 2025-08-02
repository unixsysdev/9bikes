"""
Monitor capabilities registry - defines what types of monitors are available
"""

MONITOR_CAPABILITIES = {
    "crypto_trading": {
        "description": "Monitor cryptocurrency exchanges for real-time trading data",
        "providers": {
            "binance": {
                "monitor_type": "websocket_stream",
                "template": "crypto_ws_monitor",
                "description": "Connect to Binance WebSocket for real-time crypto data",
                "required_secrets": ["api_key", "api_secret"],
                "config_template": {
                    "ws_url": "wss://stream.binance.com:9443/ws",
                    "subscription": {
                        "method": "SUBSCRIBE",
                        "params": ["{{symbol}}@trade", "{{symbol}}@depth"]
                    }
                },
                "setup_questions": [
                    {
                        "field": "symbols",
                        "prompt": "Which trading pairs do you want to monitor? (e.g., BTCUSDT, ETHUSDT)",
                        "type": "array",
                        "example": ["BTCUSDT", "ETHUSDT"]
                    },
                    {
                        "field": "data_types",
                        "prompt": "What data do you want to track?",
                        "type": "select",
                        "options": ["trades", "orderbook", "klines", "all"],
                        "default": "trades"
                    }
                ]
            },
            "coinbase": {
                "monitor_type": "websocket_stream",
                "template": "coinbase_monitor",
                "description": "Connect to Coinbase Pro WebSocket",
                "required_secrets": ["api_key", "api_secret", "passphrase"],
                "config_template": {
                    "ws_url": "wss://ws-feed.pro.coinbase.com",
                    "subscription": {
                        "type": "subscribe",
                        "channels": ["level2", "heartbeat", "ticker"]
                    }
                }
            }
        }
    },
    
    "api_monitoring": {
        "description": "Monitor REST APIs for uptime, performance, and data changes",
        "providers": {
            "generic_api": {
                "monitor_type": "api_poller",
                "template": "generic_api_monitor",
                "description": "Monitor any REST API endpoint",
                "required_secrets": [],
                "config_template": {
                    "url": "{{endpoint_url}}",
                    "method": "GET",
                    "headers": {},
                    "interval": 60
                },
                "setup_questions": [
                    {
                        "field": "endpoint_url",
                        "prompt": "What's the API endpoint URL?",
                        "type": "url",
                        "validation": "^https?://.+"
                    },
                    {
                        "field": "method",
                        "prompt": "HTTP method?",
                        "type": "select",
                        "options": ["GET", "POST", "PUT", "DELETE"],
                        "default": "GET"
                    },
                    {
                        "field": "interval",
                        "prompt": "How often should I check? (seconds)",
                        "type": "integer",
                        "default": 60,
                        "min": 10
                    },
                    {
                        "field": "auth_header",
                        "prompt": "Do you need an authorization header? (leave blank if no auth needed)",
                        "type": "secret",
                        "optional": True
                    }
                ]
            },
            "graphql": {
                "monitor_type": "graphql_poller",
                "template": "graphql_monitor",
                "description": "Monitor GraphQL APIs",
                "required_secrets": [],
                "config_template": {
                    "endpoint": "{{graphql_endpoint}}",
                    "query": "{{graphql_query}}",
                    "variables": {}
                }
            }
        }
    },
    
    "github_events": {
        "description": "Monitor GitHub repositories for commits, issues, pull requests",
        "providers": {
            "webhook": {
                "monitor_type": "webhook_receiver",
                "template": "github_webhook",
                "description": "Receive GitHub webhooks for real-time events",
                "setup_steps": [
                    "I'll create a webhook endpoint for you",
                    "Add this URL to your GitHub repo settings",
                    "Select which events to monitor"
                ],
                "setup_questions": [
                    {
                        "field": "repository",
                        "prompt": "Which repository? (format: owner/repo)",
                        "type": "string",
                        "validation": "^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$"
                    },
                    {
                        "field": "events",
                        "prompt": "Which events do you want to monitor?",
                        "type": "multiselect",
                        "options": ["push", "pull_request", "issues", "releases", "deployments"],
                        "default": ["push", "pull_request"]
                    }
                ]
            },
            "polling": {
                "monitor_type": "api_poller",
                "template": "github_api",
                "description": "Poll GitHub API for repository data",
                "required_secrets": ["github_token"],
                "endpoints": {
                    "commits": "/repos/{owner}/{repo}/commits",
                    "issues": "/repos/{owner}/{repo}/issues",
                    "pulls": "/repos/{owner}/{repo}/pulls"
                }
            }
        }
    },
    
    "email_monitoring": {
        "description": "Monitor email inboxes for specific conditions",
        "providers": {
            "gmail": {
                "monitor_type": "oauth_poller",
                "template": "gmail_monitor",
                "description": "Monitor Gmail inbox using OAuth",
                "required_auth": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
                "setup_questions": [
                    {
                        "field": "search_query",
                        "prompt": "Gmail search query (e.g., 'from:alerts@service.com')",
                        "type": "string"
                    },
                    {
                        "field": "check_interval",
                        "prompt": "Check interval in minutes",
                        "type": "integer",
                        "default": 5,
                        "min": 1
                    }
                ]
            },
            "imap": {
                "monitor_type": "imap_poller",
                "template": "imap_monitor",
                "description": "Monitor any IMAP email server",
                "required_secrets": ["host", "username", "password"],
                "config_options": ["folder", "search_criteria", "mark_as_read"]
            }
        }
    },
    
    "website_monitoring": {
        "description": "Monitor websites for changes, uptime, and performance",
        "providers": {
            "uptime": {
                "monitor_type": "http_monitor",
                "template": "uptime_monitor",
                "description": "Monitor website uptime and response times",
                "setup_questions": [
                    {
                        "field": "url",
                        "prompt": "Website URL to monitor",
                        "type": "url"
                    },
                    {
                        "field": "interval",
                        "prompt": "Check interval (seconds)",
                        "type": "integer",
                        "default": 300
                    },
                    {
                        "field": "timeout",
                        "prompt": "Request timeout (seconds)",
                        "type": "integer",
                        "default": 30
                    }
                ]
            },
            "content_change": {
                "monitor_type": "content_monitor",
                "template": "content_change_monitor",
                "description": "Monitor website content for changes",
                "setup_questions": [
                    {
                        "field": "url",
                        "prompt": "Website URL to monitor",
                        "type": "url"
                    },
                    {
                        "field": "css_selector",
                        "prompt": "CSS selector for content to monitor (optional)",
                        "type": "string",
                        "optional": True
                    },
                    {
                        "field": "check_interval",
                        "prompt": "Check interval (minutes)",
                        "type": "integer",
                        "default": 60
                    }
                ]
            }
        }
    },
    
    "database_monitoring": {
        "description": "Monitor database performance and data changes",
        "providers": {
            "mysql": {
                "monitor_type": "db_monitor",
                "template": "mysql_monitor",
                "description": "Monitor MySQL database",
                "required_secrets": ["host", "username", "password", "database"],
                "setup_questions": [
                    {
                        "field": "query",
                        "prompt": "SQL query to monitor (SELECT only)",
                        "type": "textarea"
                    },
                    {
                        "field": "interval",
                        "prompt": "Check interval (seconds)",
                        "type": "integer",
                        "default": 300
                    }
                ]
            },
            "postgres": {
                "monitor_type": "db_monitor",
                "template": "postgres_monitor",
                "description": "Monitor PostgreSQL database",
                "required_secrets": ["host", "username", "password", "database"]
            }
        }
    },
    
    "system_monitoring": {
        "description": "Monitor system resources and services",
        "providers": {
            "server_stats": {
                "monitor_type": "system_monitor",
                "template": "system_stats_monitor",
                "description": "Monitor server CPU, memory, disk usage",
                "required_secrets": ["ssh_host", "ssh_username", "ssh_key"],
                "setup_questions": [
                    {
                        "field": "metrics",
                        "prompt": "Which metrics to collect?",
                        "type": "multiselect",
                        "options": ["cpu", "memory", "disk", "network", "load"],
                        "default": ["cpu", "memory", "disk"]
                    },
                    {
                        "field": "interval",
                        "prompt": "Collection interval (seconds)",
                        "type": "integer",
                        "default": 60
                    }
                ]
            }
        }
    }
}
