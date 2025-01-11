"""Load testing service for Nova."""

import asyncio
import time
from typing import List, Dict, Any, Optional

from ..monitoring.metrics import (
    QUERY_LATENCY,
    API_REQUESTS,
    API_ERRORS,
    MEMORY_USAGE,
    VECTOR_STORE_SIZE,
    RATE_LIMITS_REMAINING
)
from ..monitoring.alerts import AlertManager


class LoadTestService:
    """Service for running load tests."""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
    async def start_test(
        self,
        queries: List[str],
        concurrent_users: int,
        duration_seconds: int,
        think_time: float = 1.0
    ) -> None:
        """Start a load test."""
        if self._running:
            raise RuntimeError("Load test already running")
            
        self._running = True
        start_time = time.time()
        
        try:
            # Create user tasks
            for i in range(concurrent_users):
                task = asyncio.create_task(
                    self._user_session(
                        i,
                        queries,
                        think_time,
                        start_time + duration_seconds
                    )
                )
                self._tasks.append(task)
                
            # Wait for duration
            await asyncio.sleep(duration_seconds)
            
            # Stop test
            self._running = False
            await self._cleanup()
            
        except Exception as e:
            self._running = False
            await self._cleanup()
            raise
            
    async def stop_test(self) -> None:
        """Stop the current load test."""
        self._running = False
        await self._cleanup()
        
    async def _cleanup(self) -> None:
        """Clean up test tasks."""
        for task in self._tasks:
            if not task.done():
                task.cancel()
                
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
    async def _user_session(
        self,
        user_id: int,
        queries: List[str],
        think_time: float,
        end_time: float
    ) -> None:
        """Simulate a user session."""
        query_index = 0
        
        while self._running and time.time() < end_time:
            try:
                # Select query
                query = queries[query_index]
                query_index = (query_index + 1) % len(queries)
                
                # Send query and measure latency
                start_time = time.time()
                try:
                    await self._process_query(query)
                    latency = time.time() - start_time
                    QUERY_LATENCY.observe(latency)
                    
                    # Check alerts
                    self.alert_manager.check_query_latency(latency)
                    
                except Exception as e:
                    API_ERRORS.inc()
                    self.alert_manager.check_error_rate(
                        API_ERRORS._value.sum(),
                        API_REQUESTS._value.sum()
                    )
                    raise
                    
                # Think time between queries
                await asyncio.sleep(think_time)
                
            except asyncio.CancelledError:
                break
                
            except Exception as e:
                # Log error but continue session
                print(f"Error in user {user_id} session: {e}")
                await asyncio.sleep(think_time)
                
    async def _process_query(self, query: str) -> None:
        """Process a single query."""
        # Track API request
        API_REQUESTS.inc()
        
        # Check rate limits
        remaining = RATE_LIMITS_REMAINING._value.get()
        if remaining <= 0:
            raise RuntimeError("Rate limit exceeded")
            
        # Simulate query processing
        await asyncio.sleep(0.1)
        
        # Update metrics
        MEMORY_USAGE.set(self._get_memory_usage())
        VECTOR_STORE_SIZE.inc()
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in bytes."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss 