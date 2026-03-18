from datetime import datetime, timezone

def generate_game_id() -> int:
    """Returns a timestamp-based numeric game id."""
    return int(datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"))
