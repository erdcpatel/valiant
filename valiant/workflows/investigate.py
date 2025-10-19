"""
Portfolio Investigation Workflow - Financial data analysis and validation

This workflow demonstrates mandatory inputs, optional inputs, and derived inputs
functionality using the unified Valiant framework.
"""

import re
from datetime import datetime, date
from typing import Dict
from valiant import Workflow, step, InputField, workflow


@workflow("investigate")
class InvestigateWorkflow(Workflow):
    """Portfolio investigation and analysis workflow"""
    
    name = "Portfolio Investigation"
    description = "Financial portfolio data investigation with mandatory, optional, and derived inputs"
    version = "1.0.0"
    author = "Valiant Team"
    tags = ["portfolio", "investigation", "financial", "analysis"]
    
    def inputs(self):
        """Define input fields for the workflow"""
        return [
            # Mandatory inputs
            InputField("portfolio_name", type="text", required=True,
                      help_text="Name of the portfolio to investigate"),
            InputField("cob_date", type="text", required=True,
                      help_text="Close of business date in YYYYMMDD format (e.g., 20241019)"),
            InputField("temporal_type", type="select", 
                      options=["EOD", "INTRADAY", "PPAR"], default="EOD",
                      help_text="Temporal type for data processing"),
            
            # Optional inputs
            InputField("region", type="select",
                      options=["US", "EU", "APAC", "GLOBAL"], default="US",
                      help_text="Geographic region for analysis"),
            InputField("include_derivatives", type="checkbox", default=False,
                      help_text="Include derivative instruments in analysis"),
            InputField("risk_threshold", type="number", min_value=0.0, max_value=100.0,
                      default=5.0, help_text="Risk threshold percentage (0-100)"),
            InputField("output_format", type="select",
                      options=["summary", "detailed", "full"], default="summary",
                      help_text="Level of detail in output report"),
            InputField("notification_email", type="email", required=False,
                      help_text="Email for investigation completion notification (optional)"),
            
            # This input can be derived if not provided
            InputField("investigation_id", type="text", required=False,
                      help_text="Custom investigation ID (auto-generated if not provided)")
        ]
    
    @step("Validate and Prepare Inputs", order=1, tags=["validation"])
    def validate_inputs(self, context: Dict):
        """Validate mandatory inputs and derive missing optional inputs"""
        portfolio_name = context.get("portfolio_name", "").strip()
        cob_date = context.get("cob_date", "").strip()
        temporal_type = context.get("temporal_type", "EOD")
        
        # Validate mandatory inputs
        if not portfolio_name:
            return self.failure("Portfolio name is required")
        
        if len(portfolio_name) < 2:
            return self.failure("Portfolio name must be at least 2 characters")
        
        # Validate COB date format (YYYYMMDD)
        if not cob_date:
            return self.failure("COB date is required")
        
        if not re.match(r'^\d{8}$', cob_date):
            return self.failure("COB date must be in YYYYMMDD format (e.g., 20241019)")
        
        # Validate the date is actually valid
        try:
            year = int(cob_date[:4])
            month = int(cob_date[4:6])
            day = int(cob_date[6:8])
            parsed_date = date(year, month, day)
            
            # Check if date is not in the future
            if parsed_date > date.today():
                return self.failure("COB date cannot be in the future")
                
        except ValueError:
            return self.failure("Invalid COB date - please check the date values")
        
        # Derive investigation_id if not provided
        investigation_id = context.get("investigation_id", "").strip()
        if not investigation_id:
            # Generate investigation ID from mandatory inputs
            portfolio_clean = re.sub(r'[^a-zA-Z0-9]', '', portfolio_name.upper())
            investigation_id = f"INV_{portfolio_clean}_{cob_date}_{temporal_type}_{datetime.now().strftime('%H%M%S')}"
            context["investigation_id"] = investigation_id
            
        # Store validated and normalized data
        context["validated_inputs"] = {
            "portfolio_name": portfolio_name.upper().strip(),
            "cob_date": cob_date,
            "temporal_type": temporal_type,
            "investigation_id": investigation_id,
            "parsed_date": parsed_date.isoformat(),
            "region": context.get("region", "US"),
            "include_derivatives": context.get("include_derivatives", False),
            "risk_threshold": float(context.get("risk_threshold") or 5.0),
            "output_format": context.get("output_format", "summary"),
            "notification_email": context.get("notification_email", "").strip() or None
        }
        
        result = self.success(f"Inputs validated for portfolio: {portfolio_name}")
        result.add_metric("portfolio_name_length", len(portfolio_name))
        result.add_metric("cob_year", year)
        result.add_metric("cob_month", month)
        result.add_metric("investigation_id_generated", investigation_id == context["investigation_id"])
        result.add_tag("input-validation")
        result.add_tag("derived-inputs")
        
        return result
    
    @step("Initialize Investigation", order=2, tags=["initialization"])
    def initialize_investigation(self, context: Dict):
        """Initialize the portfolio investigation process"""
        inputs = context.get("validated_inputs", {})
        
        if not inputs:
            return self.failure("No validated inputs found")
        
        portfolio_name = inputs["portfolio_name"]
        investigation_id = inputs["investigation_id"]
        cob_date = inputs["cob_date"]
        temporal_type = inputs["temporal_type"]
        
        # Initialize investigation context
        context["investigation_context"] = {
            "id": investigation_id,
            "portfolio": portfolio_name,
            "cob_date": cob_date,
            "temporal_type": temporal_type,
            "start_time": datetime.now().isoformat(),
            "status": "initialized",
            "data_sources": [],
            "findings": [],
            "metrics": {}
        }
        
        # Determine data sources based on temporal type
        data_sources = ["portfolio_positions", "market_data"]
        if temporal_type == "INTRADAY":
            data_sources.extend(["intraday_trades", "real_time_prices"])
        elif temporal_type == "PPAR":
            data_sources.extend(["ppar_data", "attribution_data"])
        else:  # EOD
            data_sources.extend(["eod_prices", "corporate_actions"])
        
        if inputs.get("include_derivatives", False):
            data_sources.append("derivatives_data")
        
        context["investigation_context"]["data_sources"] = data_sources
        
        result = self.success(f"Investigation {investigation_id} initialized for {portfolio_name}")
        result.add_metric("data_sources_count", len(data_sources))
        result.add_metric("temporal_type", temporal_type)
        result.add_tag("initialization")
        result.add_tag(f"region-{inputs['region'].lower()}")
        
        return result
    
    @step("Perform Data Analysis", order=3, tags=["analysis"])
    def perform_analysis(self, context: Dict):
        """Perform portfolio data analysis based on configuration"""
        inputs = context.get("validated_inputs", {})
        investigation = context.get("investigation_context", {})
        
        if not inputs or not investigation:
            return self.failure("Missing validation data or investigation context")
        
        portfolio_name = inputs["portfolio_name"]
        risk_threshold = inputs["risk_threshold"]
        include_derivatives = inputs["include_derivatives"]
        
        # Simulate analysis findings
        findings = []
        metrics = {}
        
        # Basic portfolio analysis
        findings.append(f"Portfolio {portfolio_name} analysis completed")
        metrics["total_positions"] = 150 + hash(portfolio_name) % 100
        metrics["total_market_value"] = (1000000 + hash(portfolio_name) % 5000000) / 100
        
        # Risk analysis
        calculated_risk = (hash(portfolio_name) % 20) / 2.0  # 0-10% risk
        if calculated_risk > risk_threshold:
            findings.append(f"Risk level {calculated_risk:.2f}% exceeds threshold {risk_threshold}%")
            metrics["risk_breach"] = True
        else:
            findings.append(f"Risk level {calculated_risk:.2f}% within acceptable threshold")
            metrics["risk_breach"] = False
        
        metrics["calculated_risk_percent"] = calculated_risk
        
        # Derivatives analysis (if enabled)
        if include_derivatives:
            derivative_count = hash(portfolio_name + "derivatives") % 50
            findings.append(f"Derivatives analysis: {derivative_count} derivative instruments found")
            metrics["derivative_count"] = derivative_count
            metrics["derivative_exposure"] = derivative_count * 10000  # Simplified calculation
        
        # Regional analysis
        region = inputs["region"]
        findings.append(f"Regional analysis for {region} market completed")
        
        # Update investigation context
        investigation["findings"] = findings
        investigation["metrics"] = metrics
        investigation["status"] = "analysis_complete"
        
        result = self.success(f"Analysis completed for {portfolio_name}")
        result.add_metric("findings_count", len(findings))
        result.add_metric("risk_level", calculated_risk)
        result.add_metric("positions_analyzed", metrics["total_positions"])
        result.add_tag("analysis")
        result.add_tag("risk-assessment")
        
        return result
    
    @step("Generate Investigation Report", order=4, tags=["reporting"])
    def generate_report(self, context: Dict):
        """Generate investigation report based on output format"""
        inputs = context.get("validated_inputs", {})
        investigation = context.get("investigation_context", {})
        
        if not inputs or not investigation:
            return self.failure("Missing required data for report generation")
        
        output_format = inputs["output_format"]
        investigation_id = investigation["id"]
        findings = investigation.get("findings", [])
        metrics = investigation.get("metrics", {})
        
        # Generate report based on format
        report_data = {
            "investigation_id": investigation_id,
            "portfolio": inputs["portfolio_name"],
            "cob_date": inputs["cob_date"],
            "temporal_type": inputs["temporal_type"],
            "region": inputs["region"],
            "generated_at": datetime.now().isoformat()
        }
        
        if output_format == "summary":
            report_data["summary"] = {
                "total_findings": len(findings),
                "risk_status": "BREACH" if metrics.get("risk_breach", False) else "OK",
                "total_positions": metrics.get("total_positions", 0)
            }
        elif output_format == "detailed":
            report_data["detailed"] = {
                "findings": findings[:5],  # Top 5 findings
                "key_metrics": {k: v for k, v in metrics.items() if k in ["calculated_risk_percent", "total_market_value"]},
                "data_sources": investigation.get("data_sources", [])
            }
        else:  # full
            report_data["full"] = {
                "all_findings": findings,
                "complete_metrics": metrics,
                "data_sources": investigation.get("data_sources", []),
                "processing_details": {
                    "start_time": investigation.get("start_time"),
                    "temporal_type": inputs["temporal_type"],
                    "include_derivatives": inputs["include_derivatives"]
                }
            }
        
        # Store report
        context["investigation_report"] = report_data
        
        result = self.success(f"Investigation report generated in {output_format} format")
        result.add_metric("report_format", output_format)
        result.add_metric("report_size_kb", len(str(report_data)) / 1024)
        result.add_tag("reporting")
        result.add_tag(f"format-{output_format}")
        
        return result
    
    @step("Send Notification", order=5, condition="notification_email", tags=["notification"])
    def send_notification(self, context: Dict):
        """Send notification email if email address was provided"""
        inputs = context.get("validated_inputs", {})
        investigation = context.get("investigation_context", {})
        
        notification_email = inputs.get("notification_email")
        if not notification_email:
            return self.skip("No notification email provided")
        
        investigation_id = investigation.get("id", "Unknown")
        portfolio_name = inputs.get("portfolio_name", "Unknown")
        
        # Simulate sending notification
        notification_sent = True  # In real implementation, this would call email service
        
        if notification_sent:
            result = self.success(f"Notification sent to {notification_email}")
            result.add_metric("notification_email", notification_email)
            result.add_tag("notification")
            result.add_tag("email-sent")
            return result
        else:
            return self.failure(f"Failed to send notification to {notification_email}")
    
    @step("Finalize Investigation", order=6, tags=["finalization"])
    def finalize_investigation(self, context: Dict):
        """Finalize the investigation process"""
        investigation = context.get("investigation_context", {})
        inputs = context.get("validated_inputs", {})
        
        if not investigation:
            return self.failure("No investigation context found")
        
        investigation_id = investigation.get("id", "Unknown")
        portfolio_name = inputs.get("portfolio_name", "Unknown")
        
        # Update investigation status
        investigation["status"] = "completed"
        investigation["end_time"] = datetime.now().isoformat()
        
        # Calculate total processing time
        start_time = datetime.fromisoformat(investigation.get("start_time", datetime.now().isoformat()))
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        investigation["processing_time_seconds"] = processing_time
        
        # Final summary
        total_findings = len(investigation.get("findings", []))
        metrics = investigation.get("metrics", {})
        risk_status = "BREACH" if metrics.get("risk_breach", False) else "OK"
        
        result = self.success(f"Investigation {investigation_id} completed successfully")
        result.add_metric("total_processing_time", processing_time)
        result.add_metric("total_findings", total_findings)
        result.add_metric("final_risk_status", risk_status)
        result.add_tag("finalization")
        result.add_tag("completed")
        
        return result