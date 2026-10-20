import asyncio

import pytest

from async_fetcher.services.concurrency import ConcurrencyLimiter


@pytest.mark.parametrize("limit", [0, -1])
def test_invalid_concurrency_limit(limit: int) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        ConcurrencyLimiter(limit)


@pytest.mark.asyncio
async def test_limit_property() -> None:
    limiter = ConcurrencyLimiter(3)

    assert limiter.limit == 3


@pytest.mark.asyncio
async def test_concurrency_never_exceeds_limit() -> None:
    limit = 3
    limiter = ConcurrencyLimiter(limit)
    active = 0
    peak_active = 0

    async def worker() -> None:
        nonlocal active, peak_active

        async with limiter:
            active += 1
            peak_active = max(peak_active, active)

            try:
                await asyncio.sleep(0.02)
            finally:
                active -= 1

    await asyncio.gather(*(worker() for _ in range(20)))

    assert peak_active == limit
    assert active == 0


@pytest.mark.asyncio
async def test_limiter_releases_slot_after_exception() -> None:
    limiter = ConcurrencyLimiter(1)

    with pytest.raises(RuntimeError, match="expected failure"):
        async with limiter:
            raise RuntimeError("expected failure")

    async with asyncio.timeout(1):
        async with limiter:
            assert limiter.limit == 1


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_leak_permit() -> None:
    limiter = ConcurrencyLimiter(1)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def holder() -> None:
        async with limiter:
            entered.set()
            await release.wait()

    async def waiter() -> None:
        async with limiter:
            pytest.fail("Cancelled waiter must not acquire the limiter.")

    holder_task = asyncio.create_task(holder())
    await entered.wait()

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0)
    waiter_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await waiter_task

    release.set()
    await holder_task

    async with asyncio.timeout(1):
        async with limiter:
            assert limiter.limit == 1
