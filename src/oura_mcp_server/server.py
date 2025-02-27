#!/usr/bin/env python3
"""
MCP server for Oura API integration.
This server exposes methods to query the Oura API for sleep, readiness, and resilience data.
"""

import os
from datetime import date, datetime
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP


class OuraClient:
    """Client for interacting with the Oura API."""

    BASE_URL = "https://api.ouraring.com/v2/usercollection"

    def __init__(self, access_token: str):
        """
        Initialize the Oura API client.

        Args:
            access_token: Personal access token for Oura API
        """
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.client = httpx.Client(timeout=30.0)

    def get_sleep_data(
        self, start_date: date, end_date: Optional[date] = None
    ) -> dict[str, Any]:
        """
        Get sleep data for a specific date range.

        Args:
            start_date: Start date for the query
            end_date: End date for the query (optional, defaults to start_date)

        Returns:
            Dictionary containing sleep data
        """
        if end_date is None:
            end_date = start_date

        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        url = f"{self.BASE_URL}/sleep"
        response = self.client.get(url, headers=self.headers, params=params)

        if response.status_code != 200:
            error_msg = f"Error {response.status_code}: {response.text}"
            raise Exception(error_msg)

        # Get the raw response
        raw_data = response.json()

        # Transform the data
        transformed_data = []

        for item in raw_data.get("data", []):
            # Format time durations
            awake_time = self._format_duration(item.get("awake_time", 0))
            deep_sleep_duration = self._format_duration(
                item.get("deep_sleep_duration", 0)
            )
            light_sleep_duration = self._format_duration(
                item.get("light_sleep_duration", 0)
            )
            rem_sleep_duration = self._format_duration(
                item.get("rem_sleep_duration", 0)
            )
            total_sleep_duration = self._format_duration(
                item.get("total_sleep_duration", 0)
            )
            time_in_bed = self._format_duration(item.get("time_in_bed", 0))

            # Format bedtime timestamps
            bedtime_start = self._format_time(item.get("bedtime_start", ""))
            bedtime_end = self._format_time(item.get("bedtime_end", ""))

            # Extract readiness data if available
            readiness = item.get("readiness", {})
            readiness_score = readiness.get("score") if readiness else None
            readiness_contributors = (
                readiness.get("contributors", {}) if readiness else {}
            )

            # Create transformed item
            transformed_item = {
                "day": item.get("day"),
                "bedtime_start": bedtime_start,
                "bedtime_end": bedtime_end,
                "awake_time": awake_time,
                "deep_sleep_duration": deep_sleep_duration,
                "light_sleep_duration": light_sleep_duration,
                "rem_sleep_duration": rem_sleep_duration,
                "total_sleep_duration": total_sleep_duration,
                "time_in_bed": time_in_bed,
                "efficiency": item.get("efficiency"),
                "latency": item.get("latency"),
                "restless_periods": item.get("restless_periods"),
                "average_breath": item.get("average_breath"),
                "average_heart_rate": item.get("average_heart_rate"),
                "average_hrv": item.get("average_hrv"),
                "lowest_heart_rate": item.get("lowest_heart_rate"),
            }

            # Add readiness data if available
            if readiness_score is not None:
                transformed_item["readiness_score"] = readiness_score
                transformed_item["readiness_contributors"] = readiness_contributors

            transformed_data.append(transformed_item)

        # Return with the original structure but with transformed data
        return {"data": transformed_data}

    def _format_duration(self, seconds: int) -> str:
        """
        Format duration in seconds to a human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "7 hours, 30 minutes, 15 seconds")
        """
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        if not parts:
            return "0 seconds"

        return ", ".join(parts)

    def _format_time(self, timestamp: str) -> str:
        """
        Format ISO timestamp to a time-only string.

        Args:
            timestamp: ISO timestamp string

        Returns:
            Formatted time string (e.g., "10:30 PM")
        """
        if not timestamp:
            return ""

        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%I:%M %p")
        except (ValueError, TypeError):
            return timestamp

    def get_daily_sleep_data(
        self, start_date: date, end_date: Optional[date] = None
    ) -> dict[str, Any]:
        """
        Get daily sleep data for a specific date range.

        Args:
            start_date: Start date for the query
            end_date: End date for the query (optional, defaults to start_date)

        Returns:
            Dictionary containing daily sleep data
        """
        if end_date is None:
            end_date = start_date

        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        url = f"{self.BASE_URL}/daily_sleep"
        response = self.client.get(url, headers=self.headers, params=params)

        if response.status_code != 200:
            error_msg = f"Error {response.status_code}: {response.text}"
            raise Exception(error_msg)

        # Get the raw response
        raw_data = response.json()

        # Transform the data - just return the data array directly
        transformed_data = []

        for item in raw_data.get("data", []):
            # Create transformed item without the id field
            transformed_item = {k: v for k, v in item.items() if k != "id"}

            # Format any duration fields if present
            if "total_sleep_duration" in transformed_item:
                transformed_item["total_sleep_duration"] = self._format_duration(
                    transformed_item["total_sleep_duration"]
                )

            transformed_data.append(transformed_item)

        # Return with the original structure but with transformed data
        return {"data": transformed_data}

    def get_readiness_data(
        self, start_date: date, end_date: Optional[date] = None
    ) -> dict[str, Any]:
        """
        Get readiness data for a specific date range.

        Args:
            start_date: Start date for the query
            end_date: End date for the query (optional, defaults to start_date)

        Returns:
            Dictionary containing readiness data
        """
        if end_date is None:
            end_date = start_date

        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        url = f"{self.BASE_URL}/daily_readiness"
        response = self.client.get(url, headers=self.headers, params=params)

        if response.status_code != 200:
            error_msg = f"Error {response.status_code}: {response.text}"
            raise Exception(error_msg)

        # Get the raw response
        raw_data = response.json()

        # Transform the data - just return the data array directly
        transformed_data = []

        for item in raw_data.get("data", []):
            # Create transformed item without the id field and timestamp fields
            transformed_item = {
                k: v
                for k, v in item.items()
                if k != "id" and not k.endswith("_timestamp") and k != "timestamp"
            }
            transformed_data.append(transformed_item)

        # Return with the original structure but with transformed data
        return {"data": transformed_data}

    def get_resilience_data(
        self, start_date: date, end_date: Optional[date] = None
    ) -> dict[str, Any]:
        """
        Get resilience data for a specific date range.

        Args:
            start_date: Start date for the query
            end_date: End date for the query (optional, defaults to start_date)

        Returns:
            Dictionary containing resilience data
        """
        if end_date is None:
            end_date = start_date

        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        url = f"{self.BASE_URL}/daily_resilience"
        response = self.client.get(url, headers=self.headers, params=params)

        if response.status_code != 200:
            error_msg = f"Error {response.status_code}: {response.text}"
            raise Exception(error_msg)

        # Get the raw response
        raw_data = response.json()

        # Transform the data - just return the data array directly
        transformed_data = []

        for item in raw_data.get("data", []):
            # Create transformed item without the id field
            transformed_item = {k: v for k, v in item.items() if k != "id"}
            transformed_data.append(transformed_item)

        # Return with the original structure but with transformed data
        return {"data": transformed_data}

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()


def parse_date(date_str: str) -> date:
    """
    Parse a date string in ISO format (YYYY-MM-DD).

    Args:
        date_str: Date string in ISO format

    Returns:
        Date object
    """
    try:
        return date.fromisoformat(date_str)
    except ValueError as err:
        raise ValueError(
            f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD"
        ) from err


# Create MCP server and OuraClient at module level
mcp = FastMCP("Oura API MCP Server")

# Default access token (will be overridden in main or by direct assignment)
default_token = os.environ.get("OURA_API_TOKEN")
oura_client = OuraClient(default_token) if default_token else None


# Add tools for querying sleep data
@mcp.tool()
def get_sleep_data(start_date: str, end_date: str) -> dict[str, Any]:
    """
    Get sleep data for a specific date range.

    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)

    Returns:
        Dictionary containing sleep data
    """
    if oura_client is None:
        return {"error": "Oura client not initialized. Please provide an access token."}

    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        return oura_client.get_sleep_data(start, end)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_readiness_data(start_date: str, end_date: str) -> dict[str, Any]:
    """
    Get readiness data for a specific date range.

    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)

    Returns:
        Dictionary containing readiness data
    """
    if oura_client is None:
        return {"error": "Oura client not initialized. Please provide an access token."}

    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        return oura_client.get_readiness_data(start, end)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_resilience_data(start_date: str, end_date: str) -> dict[str, Any]:
    """
    Get resilience data for a specific date range.

    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)

    Returns:
        Dictionary containing resilience data
    """
    if oura_client is None:
        return {"error": "Oura client not initialized. Please provide an access token."}

    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        return oura_client.get_resilience_data(start, end)
    except Exception as e:
        return {"error": str(e)}


# Add tools for querying today's data
@mcp.tool()
def get_today_sleep_data() -> dict[str, Any]:
    """
    Get sleep data for today.

    Returns:
        Dictionary containing sleep data for today
    """
    if oura_client is None:
        return {"error": "Oura client not initialized. Please provide an access token."}

    try:
        today = date.today()
        return oura_client.get_sleep_data(today, today)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_today_readiness_data() -> dict[str, Any]:
    """
    Get readiness data for today.

    Returns:
        Dictionary containing readiness data for today
    """
    if oura_client is None:
        return {"error": "Oura client not initialized. Please provide an access token."}

    try:
        today = date.today()
        return oura_client.get_readiness_data(today, today)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_today_resilience_data() -> dict[str, Any]:
    """
    Get resilience data for today.

    Returns:
        Dictionary containing resilience data for today
    """
    if oura_client is None:
        return {"error": "Oura client not initialized. Please provide an access token."}

    try:
        today = date.today()
        return oura_client.get_resilience_data(today, today)
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    print("Starting Oura MCP server!")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
