"""
Botni `python -m bot` orqali ishga tushirish imkoniyati.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
