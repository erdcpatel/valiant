import requests
import subprocess
import sqlalchemy
from typing import Tuple, Dict, Any, Optional
import json


def api_call(
        method: str,
        url: str,
        context: Dict,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
) -> Tuple[bool, Any]:
    """Make API call with context support."""
    try:
        # Use headers from context if not provided
        final_headers = headers or context.get("headers", {})

        # Resolve variables in URL using context
        formatted_url = url.format(**context)

        if method.upper() == "GET":
            response = requests.get(formatted_url, headers=final_headers, **kwargs)
        elif method.upper() == "POST":
            response = requests.post(formatted_url, json=data, headers=final_headers, **kwargs)
        elif method.upper() == "PUT":
            response = requests.put(formatted_url, json=data, headers=final_headers, **kwargs)
        elif method.upper() == "DELETE":
            response = requests.delete(formatted_url, headers=final_headers, **kwargs)
        else:
            return False, f"Unsupported HTTP method: {method}"

        response.raise_for_status()

        # Try to parse JSON if possible
        try:
            return True, response.json()
        except json.JSONDecodeError:
            return True, response.text
    except requests.exceptions.RequestException as e:
        return False, f"API error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def api_get(url: str, context: Dict, headers: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
    """Make GET API call."""
    return api_call("GET", url, context, headers=headers, **kwargs)


def api_post(url: str, context: Dict, data: Dict, headers: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
    """Make POST API call."""
    return api_call("POST", url, context, data=data, headers=headers, **kwargs)


def run_sql(
        context: Dict,
        query: str,
        connection_str: Optional[str] = None,
        **kwargs
) -> Tuple[bool, Any]:
    """Execute SQL query with context support."""
    try:
        # Get connection string from context if not provided
        conn_str = connection_str or context.get("DB_CONNECTION_STR")
        if not conn_str:
            return False, "Database connection string not provided"

        # Resolve variables in query using context
        formatted_query = query.format(**context)

        engine = sqlalchemy.create_engine(conn_str)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(formatted_query), **kwargs)

            # Return results as dictionaries
            if result.returns_rows:
                return True, [dict(row) for row in result.mappings()]
            return True, "Query executed successfully"
    except sqlalchemy.exc.SQLAlchemyError as e:
        return False, f"SQL error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def run_cli(
        context: Dict,
        command: str,
        capture_output: bool = True,
        **kwargs
) -> Tuple[bool, str]:
    """Execute CLI command with context support."""
    try:
        # Resolve variables in command using context
        formatted_cmd = command.format(**context)

        result = subprocess.run(
            formatted_cmd,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE,
            **kwargs
        )
        output = result.stdout if capture_output else "Command executed successfully"
        return True, output
    except subprocess.CalledProcessError as e:
        return False, e.stderr or f"Process exited with code {e.returncode}"
    except Exception as e:
        return False, f"CLI error: {str(e)}"

def get_nested(data: dict, path: str, default: Any = None) -> Any:
    """
    Access nested dictionary values using dot notation
    Example: get_nested(response, "user.address.city")
    """
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def log_response_summary(
        response: dict,
        keys: list,
        prefix: str = ""
) -> str:
    """
    Create summary message from response
    Example: log_response_summary(response, ["id", "status", "items.count"])
    """
    summary = []
    for key in keys:
        value = get_nested(response, key)
        summary.append(f"{key}: {value}")

    return prefix + " | ".join(summary)


def validate_response(
    response: dict,
    checks: dict,
    context: Optional[dict] = None,
    set_values: Optional[dict] = None
) -> Tuple[bool, str]:
    """
    Validate API response with one-liner
    Example:
        validate_response(data,
            checks={"status": "active", "count": lambda x: x > 0},
            set_values={"user_id": "id", "token": "auth.token"}
        )
    """
    errors = []
    for key, condition in checks.items():
        value = get_nested(response, key)
        if callable(condition):
            if not condition(value):
                errors.append(f"{key} failed validation")
        elif value != condition:
            errors.append(f"{key} expected {condition}, got {value}")

    if set_values and context:
        for context_key, response_key in set_values.items():
            context[context_key] = get_nested(response, response_key)

    return (len(errors) == 0, "; ".join(errors) if errors else "Validation passed")


def api_get_and_process(
        url: str,
        context: dict,
        checks: Optional[dict] = None,
        set_values: Optional[dict] = None,
        **kwargs
) -> Tuple[bool, str]:
    """
    Combined API call + validation + extraction
    Example:
        api_get_and_process("/data", context,
            checks={"status": "ok", "count": lambda x: x > 0},
            set_values={"items": "results", "total": "pagination.total"}
        )
    """
    success, response = api_get(url, context, **kwargs)
    if not success:
        return False, response

    if checks:
        valid, message = validate_response(response, checks, context, set_values)
        if not valid:
            return False, message

    if set_values and context:
        for context_key, response_key in set_values.items():
            if callable(response_key):
                context[context_key] = response_key(response)
            else:
                context[context_key] = get_nested(response, response_key)

    return True, "Request processed successfully"
