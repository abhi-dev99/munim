import asyncio
from app.agents.report_agent import generate_munim_report

async def main():
    try:
        res = await generate_munim_report("6d123264-9325-4a37-b769-274834a04085", month=6, year=2026)
        print("Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
