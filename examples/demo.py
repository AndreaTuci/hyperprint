import datetime

from hyperprint import print_info, print_exception


# --- Big, deeply nested test payload ----------------------------------------
def _today(offset=0):
    return datetime.date.today() + datetime.timedelta(days=offset)


users = [
    {
        "id": 1,
        "name": "Alice Doe",
        "email": "alice@example.com",
        "active": True,
        "joined": _today(-365),
        "roles": ["admin", "editor"],
        "profile": {
            "bio": "Senior backend engineer; loves Python, distributed systems, and espresso.",
            "location": {"city": "Milano", "country": "IT", "timezone": "Europe/Rome"},
            "social": {
                "github": "alicedoe",
                "twitter": None,
                "linkedin": "https://linkedin.com/in/alicedoe",
            },
        },
        "preferences": {
            "language": "it",
            "notifications": {"email": True, "push": False, "sms": None},
            "theme": "dark",
        },
        "stats": {
            "logins_total": 1287,
            "last_login": _today(-1),
            "projects": [ 
                
                {
                    "title": "Lorem ipsum",
                    "date": _today(-15),
                    "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                },
            ],
        },
    },
    {
        "id": 2,
        "name": "Bob Smith",
        "email": "bob@example.com",
        "active": False,
        "joined": _today(-30),
        "roles": ["viewer"],
        "profile": {
            "bio": "",
            "location": {"city": "Berlin", "country": "DE", "timezone": "Europe/Berlin"},
            "social": {"github": None, "twitter": "bsmith", "linkedin": None},
        },
        "preferences": {
            "language": "en",
            "notifications": {"email": False, "push": False, "sms": False},
            "theme": "light",
        },
        "stats": {
            "logins_total": 12,
            "last_login": _today(-25),
            "projects": [],
        },
    },
]


report = {
    "generated_at": datetime.datetime.now(),
    "version": "2.4.1",
    "environment": "production",
    "totals": {"users": len(users), "active_users": sum(1 for u in users if u["active"])},
    "feature_flags": {
        "new_dashboard": True,
        "beta_search": False,
        "experimental_ai_assist": None,
    },
    "users": users,
    "audit_trail": [
        {"ts": _today(-2), "actor": "system", "event": "snapshot", "ok": True},
        {"ts": _today(-1), "actor": "alice@example.com", "event": "login", "ok": True},
        {"ts": _today(0), "actor": "bob@example.com", "event": "failed_login", "ok": False},
    ],
}


# --- Nested-exception scenario ----------------------------------------------
def parse_config(raw: str):
    return int(raw)  # will raise ValueError on non-numeric input


def load_settings(source: str):
    try:
        return parse_config(source)
    except ValueError as e:
        # explicit chaining: raise X from Y
        raise RuntimeError(f"could not load settings from {source!r}") from e


def boot():
    config_path = "/etc/myapp/config.ini"
    raw_value = "not-a-number"
    retries_left = 0
    try:
        load_settings(raw_value)
    except RuntimeError as cause:
        # implicit chaining via "during handling" — re-raise a different one
        diagnostic = {
            "path": config_path,
            "raw": raw_value,
            "retries_left": retries_left,
            "cause": str(cause),
        }
        raise SystemError(f"boot failed: settings unavailable ({diagnostic})")


if __name__ == "__main__":
    print("BEFORE print_info")
    print_info(report, heading="Daily Report")
    print("AFTER print_info")

    print("BEFORE print_exception")
    try:
        boot()
    except Exception:
        report = print_exception()
    print("AFTER print_exception")

    if report is not None:
        print()
        print("--- report fields you can use in a real app ---")
        print(f"type        : {report.type_name}  ({report.module})")
        print(f"message     : {report.message}")
        print(f"timestamp   : {report.timestamp.isoformat(timespec='seconds')}")
        print(f"fingerprint : {report.fingerprint}")
        print(f"is_chained  : {report.is_chained}  ({len(report.chain)} exceptions)")
        print(f"root cause  : {report.root_cause.qualified_name}: {report.root_cause.message}")
        last_frame = report.last.frames[-1]
        print(f"raise site  : {last_frame.filename}:{last_frame.lineno} in {last_frame.function}")
        print(f"raise locals: {list(last_frame.locals_repr)}")
