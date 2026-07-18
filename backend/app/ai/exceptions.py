class AIError(Exception):
    safe_code = "AI_PROVIDER_UNAVAILABLE"

    def __init__(self, message: str, safe_code: str | None = None) -> None:
        super().__init__(message)
        if safe_code:
            self.safe_code = safe_code
