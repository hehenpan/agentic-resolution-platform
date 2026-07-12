from pydantic import BaseModel, Field

class ExampleAddRequest(BaseModel):
    """
    Pydantic schema representing the request parameters for the example_add tool.
    """
    a: float = Field(..., description="First value to sum")
    b: float = Field(..., description="Second value to sum")


class ExampleAddResponse(BaseModel):
    """
    Pydantic schema representing the response payload for the example_add tool.
    """
    result: float = Field(..., description="The sum result")
