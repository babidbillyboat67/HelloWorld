"""One-off helper: generates a VAPID key pair for Web Push and prints them
in the form needed for the .env file and the frontend.

    python generate_vapid_keys.py
"""

import base64

from py_vapid import Vapid02


def main():
    vapid = Vapid02()
    vapid.generate_keys()

    private_value = vapid.private_key.private_numbers().private_value
    private_raw = private_value.to_bytes(32, "big")
    private_b64 = base64.urlsafe_b64encode(private_raw).rstrip(b"=").decode()

    public_numbers = vapid.public_key.public_numbers()
    public_raw = b"\x04" + public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")
    public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode()

    print("Add these lines to canvas-notifier/backend/.env:\n")
    print(f"VAPID_PRIVATE_KEY={private_b64}")
    print(f"VAPID_PUBLIC_KEY={public_b64}")
    print("VAPID_CLAIMS_EMAIL=mailto:you@example.com")
    print("\nVAPID_PUBLIC_KEY is also pasted into the frontend automatically via /api/vapid-public-key.")


if __name__ == "__main__":
    main()
