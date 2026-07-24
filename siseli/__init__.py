"""python-siseli — Python SDK for Siseli Cloud.

Typical usage::

    import asyncio
    from siseli import SiseliClient

    async def main():
        async with SiseliClient("user@example.com", "secret") as client:
            devices = await client.get_devices()
            device = devices[0]

            state = await client.get_device_state(device.id)
            flow  = await client.get_energy_flow(device.id)

            print(state.get("gridVoltage"))
            print(flow.battery)

    asyncio.run(main())
"""

from .client import SiseliClient
from .exceptions import ApiError, AuthenticationError, NetworkError, SiseliError, TokenExpiredError
from .models import Device, DeviceState, EnergyFlow, FlowNode, StateAttribute, TokenInfo

__all__ = [
    "SiseliClient",
    # Exceptions
    "SiseliError",
    "AuthenticationError",
    "TokenExpiredError",
    "ApiError",
    "NetworkError",
    # Models
    "TokenInfo",
    "Device",
    "DeviceState",
    "EnergyFlow",
    "FlowNode",
    "StateAttribute",
]
