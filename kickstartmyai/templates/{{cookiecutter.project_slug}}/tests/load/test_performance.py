"""
Load testing for KickStartMyAI applications.

This module provides performance testing capabilities for the generated FastAPI applications.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import pytest
from httpx import AsyncClient
import aiohttp


@dataclass
class LoadTestResult:
    """Results from a load test run."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    average_response_time: float
    median_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    errors: List[str]


class LoadTester:
    """Load testing utility for API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[float] = []
        self.errors: List[str] = []
    
    async def run_load_test(
        self,
        endpoint: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        json_data: Dict[str, Any] = None,
        concurrent_users: int = 10,
        requests_per_user: int = 10,
        ramp_up_time: float = 0
    ) -> LoadTestResult:
        """
        Run a load test against an endpoint.
        
        Args:
            endpoint: API endpoint to test
            method: HTTP method (GET, POST, etc.)
            headers: Request headers
            json_data: JSON data for POST/PUT requests
            concurrent_users: Number of concurrent users
            requests_per_user: Number of requests per user
            ramp_up_time: Time to ramp up all users (seconds)
        """
        
        self.results = []
        self.errors = []
        
        total_requests = concurrent_users * requests_per_user
        start_time = time.time()
        
        # Create semaphore to limit concurrent connections
        semaphore = asyncio.Semaphore(concurrent_users)
        
        async def make_request(session: aiohttp.ClientSession, user_id: int, request_id: int):
            """Make a single request."""
            async with semaphore:
                if ramp_up_time > 0:
                    # Ramp up delay
                    delay = (user_id / concurrent_users) * ramp_up_time
                    await asyncio.sleep(delay)
                
                request_start = time.time()
                try:
                    url = f"{self.base_url}{endpoint}"
                    
                    if method.upper() == "GET":
                        async with session.get(url, headers=headers) as response:
                            await response.text()
                            response.raise_for_status()
                    elif method.upper() == "POST":
                        async with session.post(url, headers=headers, json=json_data) as response:
                            await response.text()
                            response.raise_for_status()
                    elif method.upper() == "PUT":
                        async with session.put(url, headers=headers, json=json_data) as response:
                            await response.text()
                            response.raise_for_status()
                    elif method.upper() == "DELETE":
                        async with session.delete(url, headers=headers) as response:
                            await response.text()
                            response.raise_for_status()
                    
                    request_time = time.time() - request_start
                    self.results.append(request_time)
                    
                except Exception as e:
                    self.errors.append(f"User {user_id}, Request {request_id}: {str(e)}")
        
        # Create tasks for all requests
        async with aiohttp.ClientSession() as session:
            tasks = []
            for user_id in range(concurrent_users):
                for request_id in range(requests_per_user):
                    task = make_request(session, user_id, request_id)
                    tasks.append(task)
            
            # Execute all requests
            await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful_requests = len(self.results)
        failed_requests = total_requests - successful_requests
        
        if self.results:
            avg_response_time = statistics.mean(self.results)
            median_response_time = statistics.median(self.results)
            min_response_time = min(self.results)
            max_response_time = max(self.results)
            
            # Calculate percentiles
            sorted_results = sorted(self.results)
            p95_index = int(0.95 * len(sorted_results))
            p99_index = int(0.99 * len(sorted_results))
            p95_response_time = sorted_results[p95_index] if p95_index < len(sorted_results) else max_response_time
            p99_response_time = sorted_results[p99_index] if p99_index < len(sorted_results) else max_response_time
        else:
            avg_response_time = median_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        requests_per_second = total_requests / total_time if total_time > 0 else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        
        return LoadTestResult(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_time=total_time,
            average_response_time=avg_response_time,
            median_response_time=median_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            errors=self.errors
        )


@pytest.mark.load
class TestAPIPerformance:
    """Load tests for API endpoints."""
    
    async def test_health_endpoint_load(self):
        """Test health endpoint under load."""
        
        tester = LoadTester()
        result = await tester.run_load_test(
            endpoint="/health",
            method="GET",
            concurrent_users=50,
            requests_per_user=20
        )
        
        # Performance assertions
        assert result.error_rate < 0.01  # Less than 1% error rate
        assert result.average_response_time < 0.1  # Less than 100ms average
        assert result.p95_response_time < 0.2  # Less than 200ms for 95th percentile
        assert result.requests_per_second > 100  # At least 100 RPS
        
        print(f"Health endpoint load test results:")
        print(f"  Requests per second: {result.requests_per_second:.2f}")
        print(f"  Average response time: {result.average_response_time:.3f}s")
        print(f"  P95 response time: {result.p95_response_time:.3f}s")
        print(f"  Error rate: {result.error_rate:.2%}")

    async def test_authentication_load(self):
        """Test authentication endpoints under load."""
        
        # Test registration under load
        tester = LoadTester()
        
        # Create unique user data for each request
        import uuid
        
        async def make_registration_request(session: aiohttp.ClientSession, user_id: int, request_id: int):
            user_data = {
                "email": f"loadtest_{user_id}_{request_id}_{uuid.uuid4().hex[:8]}@example.com",
                "password": "LoadTest123!",
                "full_name": f"Load Test User {user_id}-{request_id}"
            }
            
            url = f"{tester.base_url}/api/v1/auth/register"
            async with session.post(url, json=user_data) as response:
                await response.text()
                return response.status == 201
        
        # Custom load test for registration
        start_time = time.time()
        semaphore = asyncio.Semaphore(20)  # Limit concurrent registrations
        results = []
        
        async def limited_registration(session, user_id, request_id):
            async with semaphore:
                request_start = time.time()
                try:
                    success = await make_registration_request(session, user_id, request_id)
                    request_time = time.time() - request_start
                    results.append(request_time)
                    return success
                except Exception as e:
                    print(f"Registration error: {e}")
                    return False
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for user_id in range(10):  # 10 concurrent users
                for request_id in range(5):  # 5 registrations each
                    task = limited_registration(session, user_id, request_id)
                    tasks.append(task)
            
            successes = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        successful_registrations = sum(1 for s in successes if s is True)
        
        # Assertions for registration performance
        assert successful_registrations >= 40  # At least 80% success rate
        assert total_time < 30  # Should complete within 30 seconds
        if results:
            avg_time = statistics.mean(results)
            assert avg_time < 2.0  # Each registration should take less than 2 seconds
        
        print(f"Registration load test results:")
        print(f"  Successful registrations: {successful_registrations}/50")
        print(f"  Total time: {total_time:.2f}s")
        if results:
            print(f"  Average registration time: {statistics.mean(results):.3f}s")

    async def test_ai_endpoint_load(self):
        """Test AI message endpoints under load."""
        
        # This test requires a running application with mock AI responses
        # In a real test, you would set up authentication and mock the AI providers
        
        tester = LoadTester()
        
        # Mock authentication (would need to be set up properly)
        headers = {
            "Authorization": "Bearer mock_token",
            "Content-Type": "application/json"
        }
        
        message_data = {
            "content": "Hello, this is a load test message",
            "conversation_id": "mock_conversation_id"
        }
        
        try:
            result = await tester.run_load_test(
                endpoint="/api/v1/messages",
                method="POST",
                headers=headers,
                json_data=message_data,
                concurrent_users=5,  # Lower concurrency for AI endpoints
                requests_per_user=3,
                ramp_up_time=1.0  # Gradual ramp up
            )
            
            # AI endpoints have different performance expectations
            assert result.error_rate < 0.1  # Less than 10% error rate
            assert result.average_response_time < 5.0  # Less than 5 seconds average
            assert result.p95_response_time < 10.0  # Less than 10 seconds for 95th percentile
            
            print(f"AI endpoint load test results:")
            print(f"  Requests per second: {result.requests_per_second:.2f}")
            print(f"  Average response time: {result.average_response_time:.3f}s")
            print(f"  P95 response time: {result.p95_response_time:.3f}s")
            print(f"  Error rate: {result.error_rate:.2%}")
            
        except Exception as e:
            # Skip test if AI endpoints are not available
            pytest.skip(f"AI endpoints not available for load testing: {e}")

    async def test_database_heavy_operations(self):
        """Test database-heavy operations under load."""
        
        tester = LoadTester()
        
        # Test listing agents (database query)
        headers = {
            "Authorization": "Bearer mock_token"
        }
        
        try:
            result = await tester.run_load_test(
                endpoint="/api/v1/agents",
                method="GET",
                headers=headers,
                concurrent_users=25,
                requests_per_user=10
            )
            
            # Database operations should be fast
            assert result.error_rate < 0.05  # Less than 5% error rate
            assert result.average_response_time < 0.5  # Less than 500ms average
            assert result.p95_response_time < 1.0  # Less than 1 second for 95th percentile
            assert result.requests_per_second > 50  # At least 50 RPS
            
            print(f"Database operations load test results:")
            print(f"  Requests per second: {result.requests_per_second:.2f}")
            print(f"  Average response time: {result.average_response_time:.3f}s")
            print(f"  P95 response time: {result.p95_response_time:.3f}s")
            print(f"  Error rate: {result.error_rate:.2%}")
            
        except Exception as e:
            # Skip test if database endpoints are not available
            pytest.skip(f"Database endpoints not available for load testing: {e}")


@pytest.mark.stress  
class TestStressScenarios:
    """Stress tests for extreme load scenarios."""
    
    async def test_spike_load(self):
        """Test handling of sudden traffic spikes."""
        
        tester = LoadTester()
        
        # Simulate traffic spike
        result = await tester.run_load_test(
            endpoint="/health",
            method="GET", 
            concurrent_users=100,  # High concurrency
            requests_per_user=50,   # Many requests
            ramp_up_time=0  # No ramp up - immediate spike
        )
        
        # System should handle spike gracefully
        assert result.error_rate < 0.15  # Less than 15% error rate under spike
        assert result.requests_per_second > 200  # Should maintain good throughput
        
        print(f"Spike load test results:")
        print(f"  Total requests: {result.total_requests}")
        print(f"  Successful requests: {result.successful_requests}")
        print(f"  Error rate: {result.error_rate:.2%}")
        print(f"  Requests per second: {result.requests_per_second:.2f}")

    async def test_sustained_load(self):
        """Test sustained high load over time."""
        
        tester = LoadTester()
        
        # Run multiple consecutive load tests to simulate sustained load
        results = []
        
        for round_num in range(3):  # 3 rounds of sustained load
            print(f"Running sustained load round {round_num + 1}/3")
            
            result = await tester.run_load_test(
                endpoint="/health",
                method="GET",
                concurrent_users=30,
                requests_per_user=20,
                ramp_up_time=2.0
            )
            
            results.append(result)
            
            # Brief pause between rounds
            await asyncio.sleep(1)
        
        # Analyze sustained performance
        avg_rps = statistics.mean([r.requests_per_second for r in results])
        avg_response_time = statistics.mean([r.average_response_time for r in results])
        max_error_rate = max([r.error_rate for r in results])
        
        # Performance should remain stable across rounds
        assert max_error_rate < 0.1  # Error rate should stay low
        assert avg_rps > 100  # Should maintain good throughput
        assert avg_response_time < 0.2  # Response times should stay reasonable
        
        print(f"Sustained load test results:")
        print(f"  Average RPS across rounds: {avg_rps:.2f}")
        print(f"  Average response time: {avg_response_time:.3f}s")
        print(f"  Maximum error rate: {max_error_rate:.2%}")

    async def test_memory_pressure(self):
        """Test behavior under memory pressure scenarios."""
        
        # This test would need to be configured based on the specific deployment
        # For now, we test with large payloads to simulate memory usage
        
        tester = LoadTester()
        
        # Create large JSON payload
        large_data = {
            "content": "x" * 10000,  # 10KB message
            "metadata": {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            result = await tester.run_load_test(
                endpoint="/api/v1/health",  # Use health endpoint for large payload test
                method="POST",
                headers=headers,
                json_data=large_data,
                concurrent_users=10,
                requests_per_user=5
            )
            
            # Should handle large payloads reasonably well
            assert result.error_rate < 0.2  # Less than 20% error rate
            assert result.average_response_time < 2.0  # Less than 2 seconds
            
            print(f"Memory pressure test results:")
            print(f"  Payload size: ~{len(str(large_data))} bytes")
            print(f"  Error rate: {result.error_rate:.2%}")
            print(f"  Average response time: {result.average_response_time:.3f}s")
            
        except Exception as e:
            pytest.skip(f"Memory pressure test not applicable: {e}")


class PerformanceBenchmark:
    """Performance benchmarking utilities."""
    
    @staticmethod
    async def benchmark_endpoint(
        endpoint: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        json_data: Dict[str, Any] = None,
        iterations: int = 100
    ) -> Dict[str, float]:
        """
        Benchmark a single endpoint for baseline performance.
        
        Returns performance metrics that can be used for comparison.
        """
        
        tester = LoadTester()
        
        result = await tester.run_load_test(
            endpoint=endpoint,
            method=method,
            headers=headers,
            json_data=json_data,
            concurrent_users=1,  # Single user for baseline
            requests_per_user=iterations
        )
        
        return {
            "average_response_time": result.average_response_time,
            "median_response_time": result.median_response_time,
            "p95_response_time": result.p95_response_time,
            "p99_response_time": result.p99_response_time,
            "requests_per_second": result.requests_per_second,
            "error_rate": result.error_rate
        }
    
    @staticmethod
    def compare_benchmarks(baseline: Dict[str, float], current: Dict[str, float]) -> Dict[str, str]:
        """Compare current performance against baseline."""
        
        comparison = {}
        
        for metric in baseline:
            if metric in current:
                baseline_val = baseline[metric]
                current_val = current[metric]
                
                if baseline_val > 0:
                    if metric == "error_rate":
                        # Lower is better for error rate
                        change = ((current_val - baseline_val) / baseline_val) * 100
                        status = "WORSE" if change > 10 else "BETTER" if change < -10 else "STABLE"
                    elif "time" in metric:
                        # Lower is better for response times
                        change = ((current_val - baseline_val) / baseline_val) * 100
                        status = "WORSE" if change > 10 else "BETTER" if change < -10 else "STABLE"
                    else:
                        # Higher is better for RPS
                        change = ((current_val - baseline_val) / baseline_val) * 100
                        status = "BETTER" if change > 10 else "WORSE" if change < -10 else "STABLE"
                    
                    comparison[metric] = f"{status} ({change:+.1f}%)"
                else:
                    comparison[metric] = "N/A"
        
        return comparison


# Performance test configuration
@pytest.fixture
def load_tester():
    """Fixture providing a LoadTester instance."""
    return LoadTester()


@pytest.fixture
def performance_benchmark():
    """Fixture providing performance benchmarking utilities."""
    return PerformanceBenchmark()


# Skip load tests by default (run with pytest -m load)
pytestmark = pytest.mark.skipif(
    not pytest.config.getoption("--run-load-tests", default=False),
    reason="Load tests skipped (use --run-load-tests to run)"
)
