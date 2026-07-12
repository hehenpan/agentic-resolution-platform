from mcp_server.main import mcp
from mcp_server.core.database import get_session
from mcp_server.schemas.example import ExampleAddRequest, ExampleAddResponse
from mcp_server.services.calculation_service import CalculationService

@mcp.tool()
async def example_add(req: ExampleAddRequest) -> ExampleAddResponse:
    """
    Exposes a calculation tool that adds two numbers together.
    Validates inputs, delegates calculation and database recording to CalculationService,
    and returns the result.
    """
    with get_session() as session:
        service = CalculationService(session=session)
        res = service.add_and_record(req.a, req.b)
        
    return ExampleAddResponse(result=res)

