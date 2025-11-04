"""Stripe billing helpers and API endpoints for the recipe web application."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import stripe
from flask import Blueprint, Response, jsonify, request
from mysql.connector import Error as MySQLError
from mysql.connector import pooling
from stripe.error import SignatureVerificationError, StripeError

from .config import DatabaseConfig, StripeConfig

LOGGER = logging.getLogger(__name__)


class BillingError(RuntimeError):
    """Base class for billing related errors."""


class CustomerNotFound(BillingError):
    """Raised when a Stripe customer cannot be located."""


@dataclass(frozen=True)
class CustomerRecord:
    user_id: str
    email: Optional[str]
    stripe_customer_id: Optional[str]


class BillingService:
    """Coordinates Stripe billing flows backed by MySQL storage."""

    def __init__(self, pool: pooling.MySQLConnectionPool, config: StripeConfig) -> None:
        self._pool = pool
        self._config = config
        stripe.api_key = config.secret_key
        self._ensure_schema()

    @classmethod
    def from_config(
        cls, database: DatabaseConfig, stripe_config: StripeConfig
    ) -> "BillingService":
        pool = pooling.MySQLConnectionPool(
            pool_name=f"{database.pool_name}_billing",
            pool_size=database.pool_size,
            host=database.host,
            port=database.port,
            user=database.user,
            password=database.password,
            database=database.database,
            charset="utf8mb4",
            use_unicode=True,
        )
        return cls(pool, stripe_config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_checkout_session(
        self,
        user_id: str,
        email: Optional[str],
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Return a Stripe Checkout session URL for the given user."""

        customer = self._ensure_customer(user_id, email)
        if not customer.stripe_customer_id:
            raise BillingError("Stripe customer record is missing an identifier")

        try:
            session = stripe.checkout.Session.create(
                customer=customer.stripe_customer_id,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[
                    {
                        "price_data": {
                            "currency": self._config.currency,
                            "product_data": {
                                "name": self._config.product_name,
                                "description": self._config.product_description,
                            },
                            "unit_amount": self._config.unit_amount,
                            "recurring": {
                                "interval": self._config.interval,
                                "interval_count": self._config.interval_count,
                            },
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except StripeError as exc:  # pragma: no cover - network/Stripe side effect
            LOGGER.exception("Failed to create Stripe checkout session")
            raise BillingError("Unable to create Stripe checkout session") from exc
        if not session.url:
            raise BillingError("Stripe did not return a checkout URL")
        return session.url

    def create_portal_session(self, user_id: str, return_url: str) -> str:
        """Return a Stripe Billing Portal URL for the given user."""

        customer = self._get_customer(user_id)
        if not customer or not customer.stripe_customer_id:
            raise CustomerNotFound("Stripe customer not found")
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer.stripe_customer_id,
                return_url=return_url,
            )
        except StripeError as exc:  # pragma: no cover - network/Stripe side effect
            LOGGER.exception("Failed to create Stripe billing portal session")
            raise BillingError("Unable to create Stripe portal session") from exc
        if not session.url:
            raise BillingError("Stripe did not return a portal URL")
        return session.url

    def process_webhook(self, payload: str, signature: str) -> None:
        """Process a Stripe webhook payload."""

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self._config.webhook_secret
            )
        except SignatureVerificationError as exc:
            LOGGER.warning("Invalid Stripe webhook signature: %s", exc)
            raise

        event_type = event.get("type")
        data_object: Any = event.get("data", {}).get("object")

        LOGGER.info("Processing Stripe webhook event: %s", event_type)

        if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
            self._handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(data_object)
        elif event_type == "customer.deleted":
            customer_id = data_object.get("id") if isinstance(data_object, dict) else None
            if customer_id:
                self._delete_customer_by_stripe_id(customer_id)
        else:
            LOGGER.debug("Ignoring Stripe event type: %s", event_type)

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------
    def _ensure_schema(self) -> None:
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stripe_customers (
                        user_id VARCHAR(191) PRIMARY KEY,
                        email VARCHAR(255) NULL,
                        stripe_customer_id VARCHAR(255) UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                    ENGINE=InnoDB
                    DEFAULT CHARSET=utf8mb4
                    COLLATE=utf8mb4_unicode_ci
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stripe_subscriptions (
                        user_id VARCHAR(191) PRIMARY KEY,
                        stripe_customer_id VARCHAR(255) NOT NULL,
                        stripe_subscription_id VARCHAR(255) NULL,
                        status VARCHAR(64) NULL,
                        plan_type VARCHAR(64) NULL,
                        current_period_start DATETIME NULL,
                        current_period_end DATETIME NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        CONSTRAINT fk_stripe_customer
                            FOREIGN KEY (stripe_customer_id) REFERENCES stripe_customers (stripe_customer_id)
                            ON DELETE CASCADE
                    )
                    ENGINE=InnoDB
                    DEFAULT CHARSET=utf8mb4
                    COLLATE=utf8mb4_unicode_ci
                    """
                )
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

    def _ensure_customer(self, user_id: str, email: Optional[str]) -> CustomerRecord:
        customer = self._get_customer(user_id)
        if customer and customer.stripe_customer_id:
            if email and email != customer.email:
                self._update_customer_email(user_id, customer.stripe_customer_id, email)
                customer = CustomerRecord(user_id=user_id, email=email, stripe_customer_id=customer.stripe_customer_id)
            return customer

        try:
            created = stripe.Customer.create(
                email=email,
                metadata={"userId": user_id},
            )
        except StripeError as exc:  # pragma: no cover - network/Stripe side effect
            LOGGER.exception("Failed to create Stripe customer")
            raise BillingError("Unable to create Stripe customer") from exc
        customer_id = created.get("id")
        if not customer_id:
            raise BillingError("Stripe did not return a customer identifier")
        self._upsert_customer(user_id, email, customer_id)
        return CustomerRecord(user_id=user_id, email=email, stripe_customer_id=customer_id)

    def _get_customer(self, user_id: str) -> Optional[CustomerRecord]:
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(
                    "SELECT user_id, email, stripe_customer_id FROM stripe_customers WHERE user_id = %s",
                    (user_id,),
                )
                row = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        if not row:
            return None
        return CustomerRecord(
            user_id=row["user_id"],
            email=row.get("email"),
            stripe_customer_id=row.get("stripe_customer_id"),
        )

    def _find_user_by_customer_id(self, stripe_customer_id: str) -> Optional[str]:
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "SELECT user_id FROM stripe_customers WHERE stripe_customer_id = %s",
                    (stripe_customer_id,),
                )
                row = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        if not row:
            return None
        return row[0]

    def _upsert_customer(self, user_id: str, email: Optional[str], stripe_customer_id: str) -> None:
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO stripe_customers (user_id, email, stripe_customer_id)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        email = VALUES(email),
                        stripe_customer_id = VALUES(stripe_customer_id)
                    """,
                    (user_id, email, stripe_customer_id),
                )
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

    def _update_customer_email(
        self, user_id: str, stripe_customer_id: str, email: str
    ) -> None:
        try:
            stripe.Customer.modify(stripe_customer_id, email=email)
        except StripeError as exc:  # pragma: no cover - network/Stripe side effect
            LOGGER.exception("Failed to update Stripe customer email")
            raise BillingError("Unable to update Stripe customer email") from exc
        self._upsert_customer(user_id, email, stripe_customer_id)

    def _delete_customer_by_stripe_id(self, stripe_customer_id: str) -> None:
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "DELETE FROM stripe_customers WHERE stripe_customer_id = %s",
                    (stripe_customer_id,),
                )
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

    def _handle_subscription_updated(self, data_object: Any) -> None:
        subscription = self._subscription_dict(data_object)
        if not subscription:
            LOGGER.warning("Received invalid subscription payload: %s", data_object)
            return
        user_id = self._find_user_by_customer_id(subscription["stripe_customer_id"])
        if not user_id:
            LOGGER.warning(
                "Unable to associate subscription %s with a known user",
                subscription["stripe_subscription_id"],
            )
            return
        self._upsert_subscription(user_id, subscription)

    def _handle_subscription_deleted(self, data_object: Any) -> None:
        subscription = self._subscription_dict(data_object)
        if not subscription:
            LOGGER.warning("Received invalid subscription payload: %s", data_object)
            return
        user_id = self._find_user_by_customer_id(subscription["stripe_customer_id"])
        if not user_id:
            LOGGER.warning(
                "Unable to find subscription owner for customer %s", subscription["stripe_customer_id"]
            )
            return
        subscription["status"] = subscription.get("status") or "canceled"
        subscription["plan_type"] = "free"
        self._upsert_subscription(user_id, subscription)

    def _upsert_subscription(self, user_id: str, details: dict[str, Any]) -> None:
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO stripe_subscriptions (
                        user_id,
                        stripe_customer_id,
                        stripe_subscription_id,
                        status,
                        plan_type,
                        current_period_start,
                        current_period_end
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        stripe_customer_id = VALUES(stripe_customer_id),
                        stripe_subscription_id = VALUES(stripe_subscription_id),
                        status = VALUES(status),
                        plan_type = VALUES(plan_type),
                        current_period_start = VALUES(current_period_start),
                        current_period_end = VALUES(current_period_end)
                    """,
                    (
                        user_id,
                        details.get("stripe_customer_id"),
                        details.get("stripe_subscription_id"),
                        details.get("status"),
                        details.get("plan_type"),
                        details.get("current_period_start"),
                        details.get("current_period_end"),
                    ),
                )
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

    def _subscription_dict(self, data_object: Any) -> Optional[dict[str, Any]]:
        if not isinstance(data_object, dict):
            return None
        stripe_customer_id = data_object.get("customer")
        if not isinstance(stripe_customer_id, str):
            return None
        status = data_object.get("status")
        plan_type = "premium" if status in {"active", "trialing", "past_due"} else "free"
        def _convert(timestamp: Any) -> Optional[datetime]:
            if not timestamp:
                return None
            try:
                return datetime.utcfromtimestamp(int(timestamp))
            except (TypeError, ValueError, OverflowError):
                return None
        return {
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": data_object.get("id"),
            "status": status,
            "plan_type": plan_type,
            "current_period_start": _convert(data_object.get("current_period_start")),
            "current_period_end": _convert(data_object.get("current_period_end")),
        }


def register_billing_routes(app: Any, service: BillingService) -> None:
    """Register the billing blueprint on the Flask application."""

    blueprint = Blueprint("billing", __name__, url_prefix="/api/v1/billing")

    @blueprint.route("/checkout", methods=["POST"])
    def checkout() -> Response:
        payload = request.get_json(silent=True) or {}
        user_id = payload.get("userId")
        email = payload.get("email")
        success_url = payload.get("successUrl")
        cancel_url = payload.get("cancelUrl")
        if not user_id or not success_url or not cancel_url:
            return jsonify({"error": "Missing required parameters"}), 400
        try:
            url = service.create_checkout_session(user_id, email, success_url, cancel_url)
        except BillingError as exc:
            LOGGER.warning("Checkout session failed for user %s: %s", user_id, exc)
            return jsonify({"error": str(exc)}), 400
        return jsonify({"url": url})

    @blueprint.route("/portal", methods=["POST"])
    def portal() -> Response:
        payload = request.get_json(silent=True) or {}
        user_id = payload.get("userId")
        return_url = payload.get("returnUrl")
        if not user_id or not return_url:
            return jsonify({"error": "Missing required parameters"}), 400
        try:
            url = service.create_portal_session(user_id, return_url)
        except CustomerNotFound:
            return jsonify({"error": "No Stripe customer found"}), 404
        except BillingError as exc:
            LOGGER.warning("Portal session failed for user %s: %s", user_id, exc)
            return jsonify({"error": str(exc)}), 400
        return jsonify({"url": url})

    @blueprint.route("/webhook", methods=["POST"])
    def webhook() -> Response:
        signature = request.headers.get("stripe-signature")
        if not signature:
            return jsonify({"error": "Missing Stripe signature"}), 400
        payload = request.get_data(as_text=True)
        try:
            service.process_webhook(payload, signature)
        except SignatureVerificationError:
            return jsonify({"error": "Invalid signature"}), 400
        except (BillingError, MySQLError) as exc:
            LOGGER.exception("Failed to process webhook: %s", exc)
            return jsonify({"error": "Webhook processing failed"}), 500
        return jsonify({"received": True})

    app.register_blueprint(blueprint)
    app.config["BILLING_SERVICE"] = service


__all__ = ["BillingService", "register_billing_routes"]
