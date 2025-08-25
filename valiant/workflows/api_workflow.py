import asyncio
import random
from typing import Tuple
import time


def step1_login(context: dict) -> Tuple[bool, str]:
    """Step 1: Simulate login to get auth token"""
    # Simulate 10% chance of transient failure
    if random.random() < 0.1:
        time.sleep(0.5)
        return False, "Temporary login failure (simulated)"

    # Check if auth token is already in context
    if context.get("auth_token"):
        return True, "Using pre-configured auth token"

    # Simulate API call with dummy credentials
    username = context["username"]
    password = context["password"]

    # Dummy validation
    if username == "admin" and password == "secret":
        # Generate dummy response
        dummy_response = {
            "token": f"dummy_token_{random.randint(1000, 9999)}",
            "user_id": random.randint(1, 100),
            "expires_in": 3600
        }

        # Store results in context
        context["auth_token"] = dummy_response["token"]
        context["user_id"] = dummy_response["user_id"]
        context["headers"] = {"Authorization": f"Bearer {dummy_response['token']}"}
        return True, f"Login successful. User ID: {dummy_response['user_id']}"

    return False, "Invalid credentials (dummy validation: use 'admin'/'secret')"


def step2_get_user_profile(context: dict) -> Tuple[bool, str]:
    """Step 2: Simulate getting user profile"""
    # Simulate 5% chance of transient failure
    if random.random() < 0.05:
        time.sleep(0.3)
        return False, "Temporary profile service failure (simulated)"

    # Simulate API call using auth token
    auth_token = context.get("auth_token")
    if not auth_token:
        return False, "Missing auth token"

    # Dummy user profiles
    user_id = context["user_id"]
    profile = {
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "role": "user"
    }

    context["user_profile"] = profile
    return True, f"Profile retrieved: {profile['name']}"


def step3_query_orders(context: dict) -> Tuple[bool, str]:
    """Step 3: Simulate querying user orders"""
    # Simulate 15% chance of transient failure
    if random.random() < 0.15:
        time.sleep(1)
        return False, "Temporary database connection issue (simulated)"

    user_id = context.get("user_id")
    if not user_id:
        return False, "Missing user ID"

    # Generate random orders
    num_orders = random.randint(1, 5)
    products = ["Laptop", "Phone", "Tablet", "Monitor", "Headphones"]
    orders = [
        {
            "id": 1000 + i,
            "product": random.choice(products),
            "price": random.randint(50, 1000)
        } for i in range(num_orders)
    ]

    context["orders"] = orders
    total_value = sum(o["price"] for o in orders)
    return True, f"Found {len(orders)} orders. Total value: ${total_value}"


async def step4_validate_orders(context: dict) -> Tuple[bool, str]:
    """Step 4: Simulate async order validation"""
    # Simulate network delay
    await asyncio.sleep(0.5)

    orders = context.get("orders", [])
    if not orders:
        return False, "No orders to validate"

    # Simulate 10% chance of validation failure
    if random.random() < 0.1:
        return False, "Order validation failed (simulated)"

    return True, f"Validated {len(orders)} orders successfully"


def step5_deploy(context: dict) -> Tuple[bool, str]:
    """Step 5: Simulate deployment CLI command"""
    # Simulate 20% chance of deployment failure
    if random.random() < 0.2:
        return False, "Deployment failed (simulated)"

    environment = context.get("environment", "dev")
    return True, f"Successfully deployed to {environment} environment"