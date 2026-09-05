import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    from app.agents.invoice_agent import process_invoice
    
    # Use a tiny 1x1 white JPEG to test pipeline
    import base64
    # minimal valid JPEG bytes
    tiny_jpg = base64.b64decode(
        "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
        "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN"
        "DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
        "MjL/wAARCAABAAEDASIAAhEBAxEB/8QAFgABAQEAAAAAAAAAAAAAAAAGBQQH/8QAIhAAAQQC"
        "AgMAAAAAAAAAAAAAAQIDBAUREiExQf/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAA"
        "AAAAAAAAAAAAAP/aAAwDAQACEQMRAD8Amx6xqVt3F1Dbyb31MkiglKvKkhHhOOOOc96UUUV"
        "B//2Q=="
    )
    
    print("Testing invoice processing pipeline...")
    try:
        result = await process_invoice(
            trader_id="6d123264-9325-4a37-b769-274834a04085",
            image_bytes=tiny_jpg,
            mime_type="image/jpeg"
        )
        print(f"SUCCESS! ITC Status: {result.itc_verdict.status}")
        print(f"Error: {result.error}")
        print(f"Diagnosis: {result.diagnosis_hi[:200] if result.diagnosis_hi else 'None'}")
    except Exception as e:
        import traceback
        print(f"EXCEPTION: {e}")
        traceback.print_exc()

asyncio.run(test())
