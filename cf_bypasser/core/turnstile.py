import base64
import json
import logging
from collections import namedtuple
from time import monotonic, sleep
from typing import Any, Callable, Optional

from cf_bypasser.core import challenge
from cf_bypasser.core.challenge import click_turnstile, origin_of
from cf_bypasser.utils.constants import (
    CLICK_COOLDOWN_SECONDS,
    DEFAULT_TIMEOUT_MS,
    TURNSTILE_POLL_SECONDS,
    TURNSTILE_TIMEOUT_SECONDS,
)

TurnstileResult = namedtuple(
    "TurnstileResult",
    ("success", "token", "error", "elapsed_seconds"),
)

_TURNSTILE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloudflare Turnstile</title>
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" async defer></script>
    <style>
        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #f7f7f7;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        #turnstile-container {
            min-height: 70px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
    </style>
</head>
<body>
    <div id="turnstile-container"></div>
    <script>
        window.turnstileToken = null;
        window.turnstileError = null;
        window.turnstileRendered = false;

        function initTurnstile() {
            if (typeof turnstile === 'undefined') {
                setTimeout(initTurnstile, 50);
                return;
            }
            try {
                const params = {
                    sitekey: __SITEKEY__,
                    callback: function(token) {
                        window.turnstileToken = token;
                    },
                    'error-callback': function(code) {
                        window.turnstileError = String(code || 'turnstile_error');
                    },
                    'expired-callback': function() {
                        window.turnstileError = 'turnstile_expired';
                    },
                    'timeout-callback': function() {
                        window.turnstileError = 'turnstile_timeout';
                    }
                };
                const action = __ACTION__;
                if (action) params.action = action;
                const cdata = __CDATA__;
                if (cdata) params.cData = cdata;
                const pagedata = __PAGEDATA__;
                if (pagedata) params.chlPageData = pagedata;

                window.turnstileWidgetId = turnstile.render('#turnstile-container', params);
                window.turnstileRendered = true;
            } catch (err) {
                window.turnstileError = String(err && err.message ? err.message : err);
            }
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initTurnstile);
        } else {
            initTurnstile();
        }
    </script>
</body>
</html>
"""


def render_turnstile_html(
    sitekey: str,
    action: Optional[str] = None,
    cdata: Optional[str] = None,
    pagedata: Optional[str] = None,
) -> str:
    """Render the minimal Turnstile widget-only HTML with properly escaped parameters."""
    return (
        _TURNSTILE_HTML_TEMPLATE
        .replace("__SITEKEY__", json.dumps(sitekey))
        .replace("__ACTION__", json.dumps(action))
        .replace("__CDATA__", json.dumps(cdata))
        .replace("__PAGEDATA__", json.dumps(pagedata))
    )


def inject_and_solve_turnstile(
    tab: Any,
    url: str,
    sitekey: str,
    action: Optional[str] = None,
    cdata: Optional[str] = None,
    pagedata: Optional[str] = None,
    timeout: float = TURNSTILE_TIMEOUT_SECONDS,
    poll_interval: float = TURNSTILE_POLL_SECONDS,
    log: Callable[[str], None] = logging.info,
) -> TurnstileResult:
    """Inject a Turnstile widget-only page for target url into the runtime browser and wait for token."""
    start_time = monotonic()
    deadline = start_time + timeout
    widget_html = render_turnstile_html(sitekey, action, cdata, pagedata)
    origin = origin_of(url).rstrip("/")

    # 1. Attempt interception via CDP Fetch so target server is never contacted
    interception_active = False
    interception_fulfilled = False
    body_b64 = base64.b64encode(widget_html.encode("utf-8")).decode("ascii")

    def on_request_paused(**event):
        nonlocal interception_fulfilled
        req_id = event.get("requestId")
        if not req_id:
            return
        res_type = event.get("resourceType")
        req_url = event.get("request", {}).get("url", "")
        # Intercept main document request on the target origin
        if res_type == "Document" and req_url.rstrip("/").startswith(origin) and "challenges.cloudflare.com" not in req_url:
            try:
                tab.driver.run(
                    "Fetch.fulfillRequest",
                    requestId=req_id,
                    responseCode=200,
                    responseHeaders=[
                        {"name": "Content-Type", "value": "text/html; charset=utf-8"},
                        {"name": "Cache-Control", "value": "no-cache, no-store, must-revalidate"},
                    ],
                    body=body_b64,
                )
                interception_fulfilled = True
                return
            except Exception as e:
                log(f"Turnstile Fetch.fulfillRequest error: {e}")
        try:
            tab.driver.run("Fetch.continueRequest", requestId=req_id)
        except Exception:
            pass

    try:
        if hasattr(tab, "driver") and hasattr(tab.driver, "set_callback"):
            tab.driver.set_callback("Fetch.requestPaused", on_request_paused, immediate=True)
            tab.run_cdp(
                "Fetch.enable",
                patterns=[{"requestStage": "Request", "resourceType": "Document"}],
            )
            interception_active = True
    except Exception as e:
        log(f"CDP Fetch.enable not available or failed: {e}")

    try:
        log(f"Navigating to {url} to inject Turnstile widget (sitekey: {sitekey})")
        try:
            nav_timeout = max(1.0, min(timeout, DEFAULT_TIMEOUT_MS / 1000))
            tab.get(url, retry=0, timeout=nav_timeout)
        except Exception as e:
            log(f"Navigation call encountered: {e}")
    finally:
        if interception_active:
            try:
                tab.driver.set_callback("Fetch.requestPaused", None)
                tab.run_cdp("Fetch.disable")
            except Exception:
                pass

    # 2. Fallback: if document was not injected via Fetch interception, inject into the page
    if not interception_fulfilled:
        try:
            rendered = tab.run_js("return Boolean(window.turnstileRendered || window.turnstileToken)")
        except Exception:
            rendered = False

        if not rendered:
            try:
                log("CDP interception did not fire; applying DOM injection fallback")
                tab.run_js(
                    """
                    (function(sitekey, action, cdata, pagedata) {
                        document.body.innerHTML = '<div id="turnstile-container"></div>';
                        window.turnstileToken = null;
                        window.turnstileError = null;
                        window.turnstileRendered = false;
                        window.initTurnstileFallback = function() {
                            if (typeof turnstile === 'undefined') return;
                            const params = {
                                sitekey: sitekey,
                                callback: function(t) { window.turnstileToken = t; },
                                'error-callback': function(e) { window.turnstileError = String(e || 'error'); }
                            };
                            if (action) params.action = action;
                            if (cdata) params.cData = cdata;
                            if (pagedata) params.chlPageData = pagedata;
                            turnstile.render('#turnstile-container', params);
                            window.turnstileRendered = true;
                        };
                        const s = document.createElement('script');
                        s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=initTurnstileFallback';
                        s.async = true;
                        s.defer = true;
                        document.head.appendChild(s);
                    })(arguments[0], arguments[1], arguments[2], arguments[3]);
                    """,
                    sitekey,
                    action,
                    cdata,
                    pagedata,
                )
            except Exception as e:
                log(f"Fallback DOM injection failed: {e}")

    # 3. Poll for resolution or interactive Turnstile checkbox
    next_click = 0.0
    while monotonic() < deadline:
        try:
            token = tab.run_js("return window.turnstileToken")
            if token:
                elapsed = monotonic() - start_time
                log(f"Turnstile token generated successfully in {elapsed:.2f}s")
                return TurnstileResult(True, token, None, elapsed)

            err = tab.run_js("return window.turnstileError")
            if err:
                elapsed = monotonic() - start_time
                log(f"Turnstile error returned: {err}")
                return TurnstileResult(False, None, str(err), elapsed)
        except Exception as e:
            log(f"Error checking Turnstile status: {e}")

        # If interactive checkbox is rendered, click it
        now = monotonic()
        if now >= next_click:
            try:
                if click_turnstile(tab, log):
                    next_click = now + CLICK_COOLDOWN_SECONDS
            except Exception as e:
                log(f"Turnstile click attempt failed: {e}")

        sleep(poll_interval)

    elapsed = monotonic() - start_time
    log(f"Turnstile resolution timed out after {elapsed:.2f}s")
    return TurnstileResult(False, None, "timeout", elapsed)
