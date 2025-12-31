#!/usr/bin/env python3
"""Manually trigger a data sync"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.services.sync import data_sync

async def main():
    print("Triggering manual data sync...")
    await data_sync.run_sync()
    print("Sync completed!")

if __name__ == "__main__":
    asyncio.run(main())
