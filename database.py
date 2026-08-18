from __future__ import annotations

from functools import wraps
from typing import Any

import streamlit as st
import httpx
from postgrest.exceptions import APIError
from supabase import Client, create_client


class DatabaseConfigurationError(RuntimeError):
    """Raised when Supabase server credentials are not configured or unreachable."""


def _handle_connection_errors(method):
    """Turn network-level failures (Supabase unreachable/paused) into a friendly error."""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except httpx.HTTPError as error:
            raise DatabaseConfigurationError(
                "Could not connect to Supabase. Check that SUPABASE_URL is correct and the "
                "project is not paused, then redeploy."
            ) from error
    return wrapper


@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets.get("SUPABASE_URL")
    secret_key = st.secrets.get("SUPABASE_SECRET_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
    if (
        not url
        or not secret_key
        or "YOUR-PROJECT-REF" in url
        or "YOUR-NEW-SUPABASE" in secret_key
    ):
        raise DatabaseConfigurationError(
            "Set real SUPABASE_URL and SUPABASE_SECRET_KEY values in Streamlit Cloud Settings > Secrets, then redeploy."
        )
    return create_client(url, secret_key)


class SupabaseHall:
    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    def seat_label(row: int, column: int) -> str:
        return f"{chr(65 + row)}{column}"

    @_handle_connection_errors
    def add_show(
        self, show_id: str, movie_name: str, show_time: str, rows: int,
        columns: int, price: int, color: str = "#1f6fb2"
    ) -> tuple[bool, str]:
        try:
            self.client.table("shows").insert({
                "show_id": show_id,
                "movie_name": movie_name,
                "show_time": show_time,
                "total_rows": rows,
                "total_cols": columns,
                "ticket_price": price,
                "poster_color": color,
            }).execute()
            return True, "Show added successfully."
        except APIError as error:
            if getattr(error, "code", None) == "23505":
                return False, "A show with that ID already exists. Choose a different ID."
            return False, "Could not add the show. Please try again."

    @_handle_connection_errors
    def get_shows(self) -> list[dict[str, Any]]:
        response = self.client.table("shows").select("*").order("created_at").execute()
        return response.data

    @_handle_connection_errors
    def get_show(self, show_id: str) -> dict[str, Any] | None:
        response = self.client.table("shows").select("*").eq("show_id", show_id).maybe_single().execute()
        return response.data

    @_handle_connection_errors
    def update_show(self, show_id: str, movie_name: str, show_time: str, price: int, color: str) -> tuple[bool, str]:
        try:
            response = self.client.table("shows").update({
                "movie_name": movie_name,
                "show_time": show_time,
                "ticket_price": price,
                "poster_color": color,
            }).eq("show_id", show_id).execute()
            if not response.data:
                return False, "Show not found."
            return True, "Show updated successfully."
        except APIError:
            return False, "Could not update the show. Please try again."

    @_handle_connection_errors
    def delete_show(self, show_id: str) -> tuple[bool, str]:
        try:
            response = self.client.table("shows").delete().eq("show_id", show_id).execute()
            if not response.data:
                return False, "Show not found."
            return True, "Show deleted successfully."
        except APIError as error:
            if getattr(error, "code", None) == "23503":
                return False, "This show has bookings and cannot be deleted. Cancel its bookings first."
            return False, "Could not delete the show. Please try again."

    @_handle_connection_errors
    def get_seat_grid(self, show_id: str) -> list[list[bool]]:
        show = self.get_show(show_id)
        if not show:
            return []
        response = self.client.table("booking_seats").select("seat_label").eq("show_id", show_id).execute()
        booked = {seat["seat_label"] for seat in response.data}
        return [
            [self.seat_label(row, column) not in booked for column in range(show["total_cols"])]
            for row in range(show["total_rows"])
        ]

    def available_seat_count(self, show_id: str) -> int:
        return sum(row.count(True) for row in self.get_seat_grid(show_id))

    @_handle_connection_errors
    def book_seats(
        self, show_id: str, name: str, phone: str, seat_list: list[tuple[int, int]], price_per_seat: int
    ) -> tuple[bool, str, dict[str, Any] | None]:
        seat_labels = [self.seat_label(row, column) for row, column in seat_list]
        try:
            response = self.client.rpc("create_booking", {
                "p_show_id": show_id,
                "p_customer_name": name,
                "p_phone": phone,
                "p_seat_labels": seat_labels,
                "p_price_per_seat": price_per_seat,
            }).execute()
            result = response.data
            if not result["ok"]:
                return False, result["message"], None
            return True, "ok", result["booking"]
        except APIError:
            return False, "Could not complete the booking. Please try again.", None

    @_handle_connection_errors
    def cancel_booking(self, ticket_no: int) -> tuple[bool, str]:
        try:
            response = self.client.table("bookings").delete().eq("ticket_no", ticket_no).execute()
            if not response.data:
                return False, "Booking not found."
            return True, "Booking cancelled and seats released."
        except APIError:
            return False, "Could not cancel the booking. Please try again."

    @_handle_connection_errors
    def get_all_bookings(self) -> list[dict[str, Any]]:
        response = self.client.table("bookings").select("*").order("created_at", desc=True).execute()
        return response.data
