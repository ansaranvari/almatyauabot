#!/usr/bin/env python3
"""Manually trigger a data sync"""
import asyncio
import sys
import os

# Set up Django-style path manipulation
sys.path.insert(0, '/app')
os.chdir('/app')

from app.services.sync import data_sync

async def main():
    print("Triggering manual data sync...")
    await data_sync.run_sync()
    print("Sync completed!")

if __name__ == "__main__":
    asyncio.run(main())
