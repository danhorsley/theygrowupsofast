# main.py — pygbag entry point for browser deployment
# pygbag looks for: async def main() in main.py
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from app import main

asyncio.run(main())
