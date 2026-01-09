import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any, Union

API_URL = "http://127.0.0.1:8000"
TOKEN_FILE = Path(".token")


def save_token(token: str) -> None:
    with open(TOKEN_FILE, "w") as f:
        f.write(token)


def get_token() -> Optional[str]:
    if not TOKEN_FILE.exists():
        return None
    with open(TOKEN_FILE, "r") as f:
        return f.read().strip()


def do_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    auth: bool = False,
) -> Any:
    url = f"{API_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")

    if auth:
        token = get_token()
        if not token:
            print("Error: Not logged in. Run 'login' command first.")
            sys.exit(1)
        req.add_header("Authorization", f"Bearer {token}")

    if data:
        json_data = json.dumps(data).encode("utf-8")
        req.data = json_data

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                return json.loads(res_body)
            return {}
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.reason}")
        print(e.read().decode())
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Failed to connect: {e.reason}")
        print(f"Ensure the API is running at {API_URL}")
        sys.exit(1)


# --- Commands ---


def login(args: argparse.Namespace) -> None:
    # Depending on auth router config, endpoint might vary.
    # In main.py: prefix="/auth", so /auth/login
    data = {
        "username": args.username,  # Schema is OAuth2PasswordRequestForm usually checks 'username'
        "password": args.password,
    }
    # Note: OAuth2PasswordRequestForm expects form data, not JSON!
    # But our do_request sends JSON.
    # Let's adjust do_request or handle form data specifically for login.

    # Actually, create_auth_router uses OAuth2PasswordRequestForm which requires FORM data.
    # We need to send application/x-www-form-urlencoded

    params = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(f"{API_URL}/auth/login", data=params, method="POST")
    # Content-type is usually auto-added or default for urlopen/Request?
    # No, we should specify.
    # Wait, 'application/x-www-form-urlencoded' is default for data=params?
    # Python docs say: "If data is passed... correct Content-Type header should be added."
    # Actually urllib defaults to application/x-www-form-urlencoded if data is bytes.

    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            token = res["access_token"]
            save_token(token)
            print(f"Logged in successfully. Token saved to {TOKEN_FILE}.")
    except urllib.error.HTTPError as e:
        print(f"Login failed: {e.code}")
        print(e.read().decode())


def create_user(args: argparse.Namespace) -> None:
    data = {"username": args.username, "password": args.password}
    res = do_request("POST", "/users", data)
    print("User created:")
    print(json.dumps(res, indent=2))


def list_users(args: argparse.Namespace) -> None:
    res = do_request("GET", f"/users?skip={args.skip}&limit={args.limit}")
    print("Users:")
    print(json.dumps(res, indent=2))


def create_item(args: argparse.Namespace) -> None:
    data = {
        "title": args.title,
        "description": args.description,
        "owner_id": args.owner_id,
    }
    res = do_request("POST", "/items", data)

    print("Item created:")
    print(json.dumps(res, indent=2))


def list_items(args: argparse.Namespace) -> None:
    res = do_request("GET", f"/items?skip={args.skip}&limit={args.limit}")
    print("Items:")
    print(json.dumps(res, indent=2))


def get_details(args: argparse.Namespace) -> None:
    # Protected endpoint
    res = do_request("GET", f"/users/{args.id}/details", auth=True)
    print("User Details (with items):")
    print(json.dumps(res, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple App CLI")
    subparsers = parser.add_subparsers(required=True)

    # Login
    p_login = subparsers.add_parser("login")
    p_login.add_argument("username")
    p_login.add_argument("password")
    p_login.set_defaults(func=login)

    # Users
    p_user_create = subparsers.add_parser("create-user")
    p_user_create.add_argument("username")
    p_user_create.add_argument("password")
    p_user_create.set_defaults(func=create_user)

    p_user_list = subparsers.add_parser("list-users")
    p_user_list.add_argument("--skip", type=int, default=0)
    p_user_list.add_argument("--limit", type=int, default=10)
    p_user_list.set_defaults(func=list_users)

    # Items
    p_item_create = subparsers.add_parser("create-item")
    p_item_create.add_argument("title")
    p_item_create.add_argument("--description")
    p_item_create.add_argument("--owner-id", type=int, required=True)
    p_item_create.set_defaults(func=create_item)

    p_item_list = subparsers.add_parser("list-items")
    p_item_list.add_argument("--skip", type=int, default=0)
    p_item_list.add_argument("--limit", type=int, default=10)
    p_item_list.set_defaults(func=list_items)

    # Details
    p_details = subparsers.add_parser("details")
    p_details.add_argument("id", type=int)
    p_details.set_defaults(func=get_details)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    import urllib.parse

    main()
