"""API client for local Alby Hub endpoints (expert mode)."""

from __future__ import annotations

from dataclasses import dataclass

from aiohttp import ClientError, ClientSession


class AlbyHubApiError(Exception):
    """Raised when an Alby Hub API operation fails."""


@dataclass(slots=True)
class AlbyHubApiClient:
    """Small API client for optional expert-mode local API usage."""

    session: ClientSession
    hub_url: str

    def _build_url(self, path: str) -> str:
        return f"{self.hub_url.rstrip('/')}{path}"

    async def health_check(self) -> bool:
        """Return True when the local API responds healthy."""
        try:
            async with self.session.get(self._build_url("/api/health"), timeout=10) as response:
                return response.status == 200
        except (TimeoutError, ClientError):
            return False

    async def get_info(self) -> dict:
        """Fetch hub info from local API."""
        return await self._json_get("/api/info")

    async def get_balance(self) -> dict:
        """Fetch wallet balance from local API."""
        return await self._json_get("/api/wallet/balance")

    async def create_invoice(self, amount_sat: int, memo: str | None, expiry_seconds: int | None) -> dict:
        """Create a BOLT11 invoice via local API."""
        payload: dict[str, int | str] = {"amount": amount_sat}
        if memo:
            payload["description"] = memo
        if expiry_seconds:
            payload["expiry"] = expiry_seconds
        return await self._json_post("/api/invoices", payload)

    async def send_payment(self, payment_request: str) -> dict:
        """Send a payment via local API."""
        return await self._json_post("/api/payments", {"payment_request": payment_request})

    async def list_transactions(self, limit: int = 50, offset: int = 0) -> dict:
        """List recent transactions via local API."""
        return await self._json_get(f"/api/transactions?limit={limit}&offset={offset}")

    async def _json_get(self, path: str) -> dict:
        try:
            async with self.session.get(self._build_url(path), timeout=10) as response:
                if response.status >= 400:
                    raise AlbyHubApiError(f"HTTP {response.status} on GET {path}")
                return await response.json(content_type=None)
        except (TimeoutError, ClientError, ValueError) as err:
            raise AlbyHubApiError(str(err)) from err

    async def _json_post(self, path: str, payload: dict) -> dict:
        try:
            async with self.session.post(self._build_url(path), json=payload, timeout=10) as response:
                if response.status >= 400:
                    raise AlbyHubApiError(f"HTTP {response.status} on POST {path}")
                return await response.json(content_type=None)
        except (TimeoutError, ClientError, ValueError) as err:
            raise AlbyHubApiError(str(err)) from err
