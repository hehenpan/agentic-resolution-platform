from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata, CheckpointTuple
from langchain_core.runnables import RunnableConfig
from typing import Any, AsyncIterator, Optional, Union

class LazyAsyncSqliteSaver(BaseCheckpointSaver):
    """
    A lazy-loading AsyncSqliteSaver wrapper to prevent 'no running event loop' 
    errors during module import time when running inside LangGraph CLI or Uvicorn.
    """
    def __init__(self, db_file: str):
        super().__init__()
        self.db_file = db_file
        self._saver = None

    def _get_saver(self) -> Any:
        if self._saver is None:
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            conn = aiosqlite.connect(self.db_file)
            self._saver = AsyncSqliteSaver(conn)
        return self._saver

    async def aget_tuple(self, *args: Any, **kwargs: Any) -> Optional[CheckpointTuple]:
        return await self._get_saver().aget_tuple(*args, **kwargs)

    async def aput(self, *args: Any, **kwargs: Any) -> RunnableConfig:
        return await self._get_saver().aput(*args, **kwargs)

    async def aput_writes(self, *args: Any, **kwargs: Any) -> None:
        return await self._get_saver().aput_writes(*args, **kwargs)

    async def alist(self, *args: Any, **kwargs: Any) -> AsyncIterator[CheckpointTuple]:
        async for item in self._get_saver().alist(*args, **kwargs):
            yield item
