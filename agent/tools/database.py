"""
Database Tool Implementation
Handles database queries and data management
"""

import os
import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from livekit.agents import llm
import asyncpg
import sqlite3
import aiosqlite

logger = logging.getLogger(__name__)

# In-memory data store for demo (replace with real database)
demo_database = {
    "customers": [
        {"id": 1, "name": "John Doe", "email": "john@example.com", "phone": "+1234567890", "status": "active"},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "phone": "+0987654321", "status": "active"},
        {"id": 3, "name": "Bob Johnson", "email": "bob@example.com", "phone": "+1122334455", "status": "inactive"}
    ],
    "orders": [
        {"id": 101, "customer_id": 1, "date": "2024-01-15", "total": 150.00, "status": "delivered"},
        {"id": 102, "customer_id": 2, "date": "2024-01-16", "total": 75.50, "status": "processing"},
        {"id": 103, "customer_id": 1, "date": "2024-01-17", "total": 200.00, "status": "shipped"}
    ],
    "products": [
        {"id": 1001, "name": "Widget A", "price": 25.00, "stock": 100},
        {"id": 1002, "name": "Gadget B", "price": 50.00, "stock": 50},
        {"id": 1003, "name": "Tool C", "price": 75.00, "stock": 25}
    ],
    "appointments": [
        {"id": 1, "customer_name": "John Doe", "date": "2024-01-20", "time": "14:00", "service": "consultation"},
        {"id": 2, "customer_name": "Jane Smith", "date": "2024-01-21", "time": "10:00", "service": "support"}
    ]
}


class DatabaseConnection:
    """Manages database connections based on configuration"""

    def __init__(self):
        self.db_type = os.getenv("DB_TYPE", "demo")  # demo, sqlite, postgresql
        self.connection = None

    async def connect(self):
        """Establish database connection"""
        try:
            if self.db_type == "postgresql":
                self.connection = await asyncpg.connect(
                    host=os.getenv("DB_HOST", "localhost"),
                    port=int(os.getenv("DB_PORT", "5432")),
                    user=os.getenv("DB_USER", "user"),
                    password=os.getenv("DB_PASSWORD", "password"),
                    database=os.getenv("DB_NAME", "claudevoice")
                )
            elif self.db_type == "sqlite":
                db_path = os.getenv("DB_PATH", "claudevoice.db")
                self.connection = await aiosqlite.connect(db_path)
            else:
                # Use demo in-memory database
                self.connection = None
                logger.info("Using demo in-memory database")

        except Exception as e:
            logger.error(f"Database connection error: {e}")
            self.connection = None

    async def close(self):
        """Close database connection"""
        if self.connection:
            if self.db_type == "postgresql":
                await self.connection.close()
            elif self.db_type == "sqlite":
                await self.connection.close()


# Global database connection
db = DatabaseConnection()


@llm.function_tool(
    description="Query database for customer, order, product, or appointment information"
)
async def database_query(
    query_type: str,
    search_term: str = "",
    filters: str = "{}"
) -> str:
    """
    Query the database for information

    Args:
        query_type: Type of query (customers, orders, products, appointments)
        search_term: Optional search term to filter results (empty string if not provided)
        filters: Optional JSON string of filters (e.g., '{"status": "active"}'), defaults to '{}'

    Returns:
        Query results as a natural language response
    """
    import json
    try:
        # Parse filters from JSON string
        filters_dict = None
        if filters and filters != "{}":
            try:
                filters_dict = json.loads(filters)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in filters: {filters}")
        
        search = search_term if search_term else None
        
        # For demo, use in-memory database
        if db.connection is None:
            return await query_demo_database(query_type, search, filters_dict)

        # Real database queries would go here
        if db.db_type == "postgresql":
            return await query_postgresql(query_type, search, filters_dict)
        elif db.db_type == "sqlite":
            return await query_sqlite(query_type, search, filters_dict)

    except Exception as e:
        logger.error(f"Database query error: {e}")
        return "I encountered an error while querying the database. Please try again."


async def query_demo_database(
    query_type: str,
    search_term: Optional[str],
    filters: Optional[Dict[str, Any]]
) -> str:
    """Query the demo in-memory database"""
    try:
        if query_type.lower() not in demo_database:
            return f"I don't have information about {query_type}. I can help with customers, orders, products, or appointments."

        data = demo_database[query_type.lower()]
        results = data.copy()

        # Apply search term
        if search_term:
            search_lower = search_term.lower()
            results = [
                item for item in results
                if any(search_lower in str(value).lower() for value in item.values())
            ]

        # Apply filters
        if filters:
            for key, value in filters.items():
                results = [
                    item for item in results
                    if key in item and item[key] == value
                ]

        # Format response
        if not results:
            return f"I couldn't find any {query_type} matching your criteria."

        if query_type.lower() == "customers":
            return format_customer_results(results)
        elif query_type.lower() == "orders":
            return format_order_results(results)
        elif query_type.lower() == "products":
            return format_product_results(results)
        elif query_type.lower() == "appointments":
            return format_appointment_results(results)

        return f"Found {len(results)} {query_type}."

    except Exception as e:
        logger.error(f"Demo database query error: {e}")
        return "I encountered an error while searching the database."


@llm.function_tool(
    description="Get detailed information about a specific customer by name or ID"
)
async def get_customer_info(
    customer_identifier: str
) -> str:
    """
    Get customer information

    Args:
        customer_identifier: Customer name or ID

    Returns:
        Customer details
    """
    try:
        # Search in demo database
        customers = demo_database["customers"]

        # Try to find by ID first
        try:
            customer_id = int(customer_identifier)
            customer = next((c for c in customers if c["id"] == customer_id), None)
        except ValueError:
            # Search by name
            customer = next(
                (c for c in customers if customer_identifier.lower() in c["name"].lower()),
                None
            )

        if not customer:
            return f"I couldn't find a customer matching '{customer_identifier}'."

        # Get customer's orders
        orders = [o for o in demo_database["orders"] if o["customer_id"] == customer["id"]]

        response = (
            f"Customer: {customer['name']}\n"
            f"Email: {customer['email']}\n"
            f"Phone: {customer['phone']}\n"
            f"Status: {customer['status']}\n"
        )

        if orders:
            response += f"\nRecent orders: {len(orders)} total\n"
            for order in orders[:3]:  # Show last 3 orders
                response += f"- Order #{order['id']}: ${order['total']:.2f} ({order['status']})\n"

        return response

    except Exception as e:
        logger.error(f"Get customer info error: {e}")
        return "I encountered an error while retrieving customer information."


@llm.function_tool(
    description="Check product inventory and availability"
)
async def check_inventory(
    product_name: str
) -> str:
    """
    Check product inventory

    Args:
        product_name: Name of the product to check

    Returns:
        Inventory status
    """
    try:
        products = demo_database["products"]
        product = next(
            (p for p in products if product_name.lower() in p["name"].lower()),
            None
        )

        if not product:
            return f"I couldn't find a product matching '{product_name}'."

        stock_status = "in stock" if product["stock"] > 10 else "low stock" if product["stock"] > 0 else "out of stock"

        return (
            f"{product['name']} - Price: ${product['price']:.2f}\n"
            f"Current inventory: {product['stock']} units ({stock_status})"
        )

    except Exception as e:
        logger.error(f"Inventory check error: {e}")
        return "I encountered an error while checking inventory."


@llm.function_tool(
    description="Add or update information in the database"
)
async def update_database(
    table: str,
    operation: str,
    data: Dict[str, Any]
) -> str:
    """
    Update database information

    Args:
        table: Table name (customers, orders, products, appointments)
        operation: Operation type (add, update, delete)
        data: Data to add or update

    Returns:
        Confirmation message
    """
    try:
        if table.lower() not in demo_database:
            return f"I don't have access to the {table} table."

        if operation.lower() == "add":
            # Generate new ID
            existing_ids = [item.get("id", 0) for item in demo_database[table.lower()]]
            new_id = max(existing_ids) + 1 if existing_ids else 1
            data["id"] = new_id

            # Add timestamp
            data["created_at"] = datetime.now().isoformat()

            # Add to database
            demo_database[table.lower()].append(data)

            return f"Successfully added new {table.rstrip('s')} with ID {new_id}."

        elif operation.lower() == "update":
            if "id" not in data:
                return "Please provide an ID for the record to update."

            # Find and update record
            records = demo_database[table.lower()]
            record = next((r for r in records if r.get("id") == data["id"]), None)

            if not record:
                return f"Could not find {table.rstrip('s')} with ID {data['id']}."

            # Update fields
            record.update(data)
            return f"Successfully updated {table.rstrip('s')} {data['id']}."

        elif operation.lower() == "delete":
            if "id" not in data:
                return "Please provide an ID for the record to delete."

            # Remove record
            records = demo_database[table.lower()]
            original_length = len(records)
            demo_database[table.lower()] = [r for r in records if r.get("id") != data["id"]]

            if len(demo_database[table.lower()]) < original_length:
                return f"Successfully deleted {table.rstrip('s')} {data['id']}."
            else:
                return f"Could not find {table.rstrip('s')} with ID {data['id']}."

        else:
            return f"Unknown operation '{operation}'. Please use 'add', 'update', or 'delete'."

    except Exception as e:
        logger.error(f"Database update error: {e}")
        return "I encountered an error while updating the database."


# Helper functions for formatting results

def format_customer_results(customers: List[Dict]) -> str:
    """Format customer query results"""
    if len(customers) == 1:
        c = customers[0]
        return (
            f"Found customer: {c['name']}, "
            f"email: {c['email']}, "
            f"phone: {c['phone']}, "
            f"status: {c['status']}"
        )
    else:
        response = f"Found {len(customers)} customers:\n"
        for c in customers[:5]:  # Limit to 5 for voice response
            response += f"- {c['name']} ({c['status']})\n"
        if len(customers) > 5:
            response += f"... and {len(customers) - 5} more"
        return response


def format_order_results(orders: List[Dict]) -> str:
    """Format order query results"""
    if len(orders) == 1:
        o = orders[0]
        return (
            f"Order {o['id']}: "
            f"${o['total']:.2f}, "
            f"date: {o['date']}, "
            f"status: {o['status']}"
        )
    else:
        response = f"Found {len(orders)} orders:\n"
        total_value = sum(o['total'] for o in orders)
        for o in orders[:5]:
            response += f"- Order {o['id']}: ${o['total']:.2f} ({o['status']})\n"
        response += f"Total value: ${total_value:.2f}"
        return response


def format_product_results(products: List[Dict]) -> str:
    """Format product query results"""
    if len(products) == 1:
        p = products[0]
        stock_status = "in stock" if p['stock'] > 10 else "low stock" if p['stock'] > 0 else "out of stock"
        return (
            f"{p['name']}: "
            f"${p['price']:.2f}, "
            f"{p['stock']} units {stock_status}"
        )
    else:
        response = f"Found {len(products)} products:\n"
        for p in products[:5]:
            response += f"- {p['name']}: ${p['price']:.2f} ({p['stock']} units)\n"
        return response


def format_appointment_results(appointments: List[Dict]) -> str:
    """Format appointment query results"""
    if len(appointments) == 1:
        a = appointments[0]
        return (
            f"Appointment with {a['customer_name']} "
            f"on {a['date']} at {a['time']} "
            f"for {a['service']}"
        )
    else:
        response = f"Found {len(appointments)} appointments:\n"
        for a in appointments[:5]:
            response += f"- {a['date']} at {a['time']}: {a['customer_name']} ({a['service']})\n"
        return response


# PostgreSQL implementation (placeholder)
async def query_postgresql(query_type: str, search_term: Optional[str], filters: Optional[Dict]) -> str:
    """Query PostgreSQL database"""
    # This would contain actual PostgreSQL queries using asyncpg
    return "PostgreSQL queries not yet implemented"


# SQLite implementation (placeholder)
async def query_sqlite(query_type: str, search_term: Optional[str], filters: Optional[Dict]) -> str:
    """Query SQLite database"""
    # This would contain actual SQLite queries using aiosqlite
    return "SQLite queries not yet implemented"