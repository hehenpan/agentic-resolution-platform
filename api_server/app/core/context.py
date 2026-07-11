from starlette_context import context



def get_request_id()->str:
    if context.exists() and "X-Request-ID" in context.data:
        return context.data["X-Request-ID"]
    return "system"