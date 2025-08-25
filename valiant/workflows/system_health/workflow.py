import asyncio
import time
import random
import json
import os
import re
import socket
import platform
from datetime import datetime
from typing import Dict, List, Tuple
from valiant.framework.workflow import BaseWorkflow, InputField, InputType
from valiant.framework.utils import run_cli


class SystemHealthWorkflow(BaseWorkflow):
    name = "System Health Check Workflow"
    description = "Comprehensive system health check with API simulations and CLI commands"

    def __init__(self, runner=None):
        self.runner = runner

    def get_input_fields(self) -> List[InputField]:
        return [
            InputField(
                name="api_endpoint",
                type=InputType.TEXT,
                label="API Endpoint",
                default="https://api.example.com/health",
                help_text="API endpoint for health check (simulated)"
            ),
            InputField(
                name="disk_path",
                type=InputType.TEXT,
                label="Disk Path",
                default="/",
                help_text="Disk path to check"
            ),
            InputField(
                name="cpu_threshold",
                type=InputType.NUMBER,
                label="CPU Usage Warning Threshold (%)",
                default=80,
                min_value=1,
                max_value=100,
                help_text="CPU usage warning threshold"
            ),
            InputField(
                name="mem_threshold",
                type=InputType.NUMBER,
                label="Memory Usage Warning Threshold (%)",
                default=80,
                min_value=1,
                max_value=100,
                help_text="Memory usage warning threshold"
            ),
            InputField(
                name="disk_threshold",
                type=InputType.NUMBER,
                label="Disk Usage Warning Threshold (%)",
                default=80,
                min_value=1,
                max_value=100,
                help_text="Disk usage warning threshold"
            ),
        ]

    def get_required_inputs(self) -> List[Tuple[str, str, bool]]:
        fields = self.get_input_fields()
        return [
            (field.label, field.name, field.type == InputType.PASSWORD)
            for field in fields
        ]

    def setup(self):
        # Set default thresholds if not provided
        self.runner.context.setdefault("cpu_threshold", 80)
        self.runner.context.setdefault("mem_threshold", 80)
        self.runner.context.setdefault("disk_threshold", 80)
        # Set default disk path if not provided
        if "disk_path" not in self.runner.context:
            self.runner.context["disk_path"] = "/"
        if "api_endpoint" not in self.runner.context:
            self.runner.context["api_endpoint"] = "https://api.example.com/health"

    def define_steps(self):
        # System information steps
        self.runner.add_step("Get-System-Info", self.step_get_system_info)
        self.runner.add_step("Check-Internet", self.step_check_internet)
        # Resource monitoring steps (run in parallel)
        self.runner.add_step("Check-CPU", self.step_check_cpu, parallel_group="resources")
        # self.runner.add_step("Check-Memory", self.step_check_memory, parallel_group="resources")
        # self.runner.add_step("Check-Disk", self.step_check_disk, parallel_group="resources")
        # Security checks
        self.runner.add_step("Check-Open-Ports", self.step_check_open_ports)
        # Report generation
        self.runner.add_step("Generate-Report", self.step_generate_report)

    # Step implementations

    def step_get_system_info(self, context: Dict) -> Tuple[bool, str, object]:
        """Get basic system information"""
        try:
            context["system_info"] = {
                "hostname": socket.gethostname(),
                "os": platform.system(),
                "os_version": platform.version(),
                "platform": platform.platform(),
                "processor": platform.processor(),
                "cpu_cores": os.cpu_count(),
                "timestamp": datetime.now().isoformat()
            }
            return True, f"System: {context['system_info']['os']} {context['system_info']['os_version']}", context["system_info"]
        except Exception as e:
            return False, f"Error getting system info: {str(e)}", None

    def step_check_internet(self, context: Dict) -> Tuple[bool, str, object]:
        """Check internet connectivity"""
        try:
            socket.gethostbyname("google.com")
            return True, "Internet connection is active", None
        except socket.error:
            return False, "No internet connection", None

    def step_check_cpu(self, context: Dict) -> Tuple[bool, str, object]:
        """Check CPU usage"""
        try:
            success, output = run_cli(context, "top -l 1 -s 0 | grep 'CPU usage'")
            if not success:
                return False, output, None
            match = re.search(r'(\d+\.\d+)% user', output)
            if not match:
                return False, "Failed to parse CPU usage", None
            cpu_usage = float(match.group(1))
            context["cpu_usage"] = cpu_usage
            threshold = context["cpu_threshold"]
            if cpu_usage > threshold:
                return False, f"High CPU usage: {cpu_usage}% (threshold: {threshold}%)", cpu_usage
            return True, f"CPU usage: {cpu_usage}%", cpu_usage
        except Exception as e:
            return False, f"Error checking CPU: {str(e)}", None

    def step_check_memory(self, context: Dict) -> Tuple[bool, str, object]:
        """Check memory usage"""
        try:
            success, output = run_cli(context, "vm_stat")
            if not success:
                return False, output, None
            lines = output.split('\n')
            stats = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    stats[key.strip()] = int(value.strip().rstrip('.'))
            page_size = 4096  # bytes
            free_mem = stats.get("Pages free", 0) * page_size
            active_mem = stats.get("Pages active", 0) * page_size
            total_mem = (free_mem + active_mem) / (1024 ** 3)  # in GB
            if total_mem <= 0:
                return False, "Failed to calculate memory usage", None
            mem_usage = (active_mem / (free_mem + active_mem)) * 100
            context["mem_usage"] = mem_usage
            threshold = context["mem_threshold"]
            if mem_usage > threshold:
                return False, f"High memory usage: {mem_usage:.1f}% (threshold: {threshold}%)", mem_usage
            return True, f"Memory usage: {mem_usage:.1f}%", mem_usage
        except Exception as e:
            return False, f"Error checking memory: {str(e)}", None

    def step_check_disk(self, context: Dict) -> Tuple[bool, str, object]:
        """Check disk usage"""
        try:
            disk_path = context["disk_path"]
            success, output = run_cli(context, f"df -h {disk_path}")
            if not success:
                return False, output, None
            lines = output.split('\n')
            if len(lines) < 2:
                return False, "Failed to parse disk usage", None
            parts = lines[1].split()
            if len(parts) < 5:
                return False, "Failed to parse disk usage", None
            usage_percent = int(parts[4].rstrip('%'))
            context["disk_usage"] = usage_percent
            threshold = context["disk_threshold"]
            if usage_percent > threshold:
                return False, f"High disk usage: {usage_percent}% (threshold: {threshold}%)", usage_percent
            return True, f"Disk usage: {usage_percent}%", usage_percent
        except Exception as e:
            return False, f"Error checking disk: {str(e)}", None

    def step_api_healthcheck(self, context: Dict) -> Tuple[bool, str, object]:
        """Simulate API health check"""
        try:
            time.sleep(1.0)
            if random.random() < 0.1:
                return False, "API health check failed (simulated)", None
            context["api_token"] = f"token_{random.randint(1000, 9999)}"
            return True, "API health check passed", context["api_token"]
        except Exception as e:
            return False, f"API error: {str(e)}", None

    def step_api_get_data(self, context: Dict) -> Tuple[bool, str, object]:
        """Simulate API data retrieval"""
        try:
            time.sleep(0.5)
            if random.random() < 0.05:
                return False, "API data retrieval failed (simulated)", None
            context["api_data"] = {
                "status": "active",
                "users": random.randint(100, 500),
                "last_updated": datetime.now().isoformat()
            }
            return True, f"Retrieved data: {context['api_data']['users']} users", context["api_data"]
        except Exception as e:
            return False, f"API error: {str(e)}", None

    def step_check_open_ports(self, context: Dict) -> Tuple[bool, str, object]:
        """Check for commonly exploited open ports"""
        try:
            success, output = run_cli(context, "netstat -tuln")
            if not success:
                return False, output, None
            dangerous_ports = [22, 23, 80, 443, 3389]
            open_ports = []
            for line in output.split('\n'):
                if 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) > 3 and '.' in parts[3]:
                        port = int(parts[3].split(':')[-1])
                        if port in dangerous_ports:
                            open_ports.append(port)
            if open_ports:
                context["open_ports"] = open_ports
                return True, f"Open ports detected: {', '.join(map(str, open_ports))}", open_ports
            return True, "No dangerous open ports detected", []
        except Exception as e:
            return False, f"Error checking ports: {str(e)}", None

    def step_generate_report(self, context: Dict) -> Tuple[bool, str, object]:
        """Generate a health check report"""
        try:
            report = {
                "system_info": context.get("system_info", {}),
                "resources": {
                    "cpu_usage": context.get("cpu_usage", 0),
                    "mem_usage": context.get("mem_usage", 0),
                    "disk_usage": context.get("disk_usage", 0),
                },
                "api_data": context.get("api_data", {}),
                "open_ports": context.get("open_ports", []),
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy"
            }
            # Check for any failures
            if any(not result.success for result in self.runner.results if result.executed):
                report["overall_status"] = "issues_detected"
            filename = f"system_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            context["report_file"] = filename
            return True, f"Report generated: {filename}", filename
        except Exception as e:
            return False, f"Error generating report: {str(e)}", None

    # Bonus: Additional CLI commands that can be added to the workflow
    def step_get_network_info(self, context: Dict) -> Tuple[bool, str, object]:
        """Get detailed network information"""
        success, output = run_cli(context, "ifconfig", capture_output=True)
        return success, output, output

    def step_check_running_processes(self, context: Dict) -> Tuple[bool, str, object]:
        """Check top running processes"""
        success, output = run_cli(context, "ps aux --sort=-%cpu | head -n 6", capture_output=True)
        return success, output, output

    def step_check_temperature(self, context: Dict) -> Tuple[bool, str, object]:
        """Check system temperature (works on some systems)"""
        success, output = run_cli(context, "sensors", capture_output=True)
        return success,