"""Flask views for the access gate."""
from __future__ import annotations

from typing import Any, Dict, Optional

from flask import (
    Blueprint,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .access_service import (
    AccessService,
    RequestCodeResult,
    RequestCodeStatus,
    VerifyCodeResult,
    VerifyCodeStatus,
)


def register_access_routes(app: Any, service: AccessService) -> None:
    """Register the access control blueprint."""

    blueprint = Blueprint("access", __name__)

    @blueprint.route("/welcome", methods=["GET", "POST"])
    def welcome() -> Any:
        device_id = request.cookies.get(service.cookie_name)
        if service.is_device_authorized(device_id):
            return redirect(url_for("recipes.index"))

        subscribe_status: Optional[Dict[str, str]] = None
        invite_status: Optional[Dict[str, str]] = None
        pending_phone = session.get("pending_invite_phone")
        pending_display = session.get("pending_invite_display")
        code_requested = bool(pending_phone)

        if request.method == "POST":
            action = request.form.get("action")
            if action == "subscribe":
                email = request.form.get("email", "")
                try:
                    service.subscribe(email)
                    subscribe_status = {
                        "category": "success",
                        "message": "Thanks! We'll keep you updated on our progress.",
                    }
                except ValueError:
                    subscribe_status = {
                        "category": "error",
                        "message": "Please enter a valid email address.",
                    }
            elif action == "request_code":
                phone_input = request.form.get("phone", "")
                result = service.request_access_code(phone_input)
                if result.status is RequestCodeStatus.SENT:
                    session["pending_invite_phone"] = result.phone_number
                    session["pending_invite_display"] = phone_input.strip()
                    pending_phone = result.phone_number
                    pending_display = phone_input.strip()
                    code_requested = True
                    invite_status = {
                        "category": "success",
                        "message": "A verification code has been sent to your mobile number.",
                    }
                elif (
                    result.status is RequestCodeStatus.ALREADY_VERIFIED
                    and result.device_id
                ):
                    response = make_response(redirect(url_for("recipes.index")))
                    response.set_cookie(
                        service.cookie_name,
                        result.device_id,
                        max_age=60 * 60 * 24 * 365,
                        httponly=True,
                        samesite="Lax",
                    )
                    session.pop("pending_invite_phone", None)
                    session.pop("pending_invite_display", None)
                    return response
                else:
                    invite_status = _map_request_error(result)
                    session.pop("pending_invite_phone", None)
                    session.pop("pending_invite_display", None)
                    pending_phone = None
                    pending_display = None
                    code_requested = False
            elif action == "verify_code":
                code = request.form.get("code", "")
                if not code.strip():
                    invite_status = {
                        "category": "error",
                        "message": "Please enter the 6-digit code we sent to you.",
                    }
                else:
                    phone_number = pending_phone or request.form.get("phone", "")
                    if not phone_number:
                        invite_status = {
                            "category": "error",
                            "message": "We couldn't determine which number to verify. Request a new code.",
                        }
                    else:
                        existing_device = request.cookies.get(service.cookie_name)
                        device_id = existing_device or service.generate_device_id()
                        result = service.verify_access_code(phone_number, code, device_id)
                        if result.status is VerifyCodeStatus.VERIFIED:
                            response = make_response(redirect(url_for("recipes.index")))
                            response.set_cookie(
                                service.cookie_name,
                                result.device_id or device_id,
                                max_age=60 * 60 * 24 * 365,
                                httponly=True,
                                samesite="Lax",
                            )
                            session.pop("pending_invite_phone", None)
                            session.pop("pending_invite_display", None)
                            return response
                        if (
                            result.status is VerifyCodeStatus.ALREADY_VERIFIED
                            and result.device_id
                        ):
                            response = make_response(redirect(url_for("recipes.index")))
                            response.set_cookie(
                                service.cookie_name,
                                result.device_id,
                                max_age=60 * 60 * 24 * 365,
                                httponly=True,
                                samesite="Lax",
                            )
                            session.pop("pending_invite_phone", None)
                            session.pop("pending_invite_display", None)
                            return response
                        invite_status = _map_verify_error(result)
                        if result.status in (
                            VerifyCodeStatus.EXPIRED,
                            VerifyCodeStatus.NOT_FOUND,
                        ):
                            session.pop("pending_invite_phone", None)
                            session.pop("pending_invite_display", None)
                            pending_phone = None
                            pending_display = None
                            code_requested = False
                        else:
                            code_requested = True
        return render_template(
            "access/welcome.html",
            subscribe_status=subscribe_status,
            invite_status=invite_status,
            code_requested=code_requested,
            pending_phone=pending_display,
        )

    app.register_blueprint(blueprint)


def _map_request_error(result: RequestCodeResult) -> Dict[str, str]:
    if result.status is RequestCodeStatus.INVALID_NUMBER:
        message = "Please enter a valid mobile number including your country code."
    elif result.status is RequestCodeStatus.NOT_FOUND:
        message = "This mobile number is not on our invite list yet."
    else:
        message = "We couldn't send a code right now. Please try again shortly."
    return {"category": "error", "message": message}


def _map_verify_error(result: VerifyCodeResult) -> Dict[str, str]:
    if result.status is VerifyCodeStatus.INVALID:
        message = "That code doesn't look right. Please try again."
    elif result.status is VerifyCodeStatus.EXPIRED:
        message = "Your code has expired. Request a new one to continue."
    elif result.status is VerifyCodeStatus.NOT_FOUND:
        message = "We couldn't find an invite for that number."
    else:
        message = "We couldn't verify the code. Please request a new one."
    return {"category": "error", "message": message}
