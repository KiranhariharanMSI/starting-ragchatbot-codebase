#!/usr/bin/env python3
"""
Debug the chat in real-time to see what's actually happening
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_live_chat():
    print("🔍 Live Chat Debugging - Real Time Test...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser window
        page = await browser.new_page()
        
        # Log everything
        page.on("console", lambda msg: print(f"🖥️ {msg.type.upper()}: {msg.text}"))
        page.on("pageerror", lambda msg: print(f"❌ ERROR: {msg}"))
        page.on("request", lambda req: print(f"📤 {req.method} {req.url}"))
        page.on("response", lambda res: print(f"📥 {res.status} {res.url}"))
        
        # Go to the app
        print("🌐 Opening http://127.0.0.1:8000...")
        await page.goto("http://127.0.0.1:8000")
        
        # Wait for it to load
        await page.wait_for_selector("#chatInput", timeout=10000)
        print("✅ Page loaded, chat input ready")
        
        # Show initial state
        messages = await page.locator('.message').count()
        print(f"📊 Initial messages: {messages}")
        
        # Take screenshot
        await page.screenshot(path="live_test_initial.png")
        
        # Type a simple question
        test_question = "Hello, what can you help me with?"
        print(f"\n📝 Typing: '{test_question}'")
        await page.fill("#chatInput", test_question)
        
        # Take screenshot after typing
        await page.screenshot(path="live_test_typed.png")
        
        # Click send
        print("🔄 Clicking send button...")
        await page.click("#sendButton")
        
        # Monitor what happens step by step
        for i in range(10):  # Check for 10 seconds
            await page.wait_for_timeout(1000)  # Wait 1 second
            
            messages = await page.locator('.message').count()
            user_messages = await page.locator('.message.user').count() 
            assistant_messages = await page.locator('.message.assistant:not(.welcome-message)').count()
            loading = await page.locator('.loading').count()
            
            print(f"⏱️  {i+1}s - Messages: {messages}, User: {user_messages}, Assistant: {assistant_messages}, Loading: {loading}")
            
            if assistant_messages > 0:
                print("✅ Assistant response appeared!")
                break
        
        # Final screenshot
        await page.screenshot(path="live_test_final.png")
        
        # Get final state
        final_messages = await page.locator('.message').count()
        final_user = await page.locator('.message.user').count()
        final_assistant = await page.locator('.message.assistant:not(.welcome-message)').count()
        
        print(f"\n📊 Final State:")
        print(f"   Total messages: {final_messages}")
        print(f"   User messages: {final_user}")
        print(f"   Assistant messages: {final_assistant}")
        
        if final_assistant > 0:
            response_text = await page.locator('.message.assistant:not(.welcome-message)').last.inner_text()
            print(f"   💬 Response: {response_text[:200]}...")
        else:
            print("   ❌ No assistant response received")
            
            # Check for any error elements
            error_count = await page.locator('.error').count()
            print(f"   🚨 Error elements: {error_count}")
            
            # Check what's in the chat messages container
            chat_html = await page.locator('#chatMessages').inner_html()
            print(f"   🔍 Chat HTML length: {len(chat_html)} characters")
        
        input("Press Enter to close browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_live_chat())