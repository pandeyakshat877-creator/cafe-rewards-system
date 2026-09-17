"""
Helper functions. QR generation now; real SMTP email sending slots in here
later, replacing the SIMULATE_EMAIL log-only path.
"""
import base64
from io import BytesIO

import qrcode


def generate_qr_code_base64(data: str) -> str:
    """Returns a base64 PNG string (no data: prefix), ready to drop into
    Jinja2 as <img src="data:image/png;base64,{{ qr }}">."""
    img = qrcode.make(data)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")