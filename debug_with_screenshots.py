#!/usr/bin/env python3
"""
Debug frontend chat functionality with screenshots
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_with_screenshots():
    print("🔍 Debugging Frontend Chat with Screenshots...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"🖥️ CONSOLE: {msg.text}"))
        page.on("pageerror", lambda msg: print(f"❌ PAGE ERROR: {msg}"))
        
        # Navigate to the app
        await page.goto("http://127.0.0.1:8000")
        print("✅ Page loaded")
        await page.screenshot(path="screenshot_1_page_loaded.png")
        
        # Wait for page to be ready
        await page.wait_for_selector("#chatInput", timeout=10000)
        print("✅ Chat input ready")
        await page.screenshot(path="screenshot_2_chat_ready.png")
        
        # Check initial state
        messages_count = await page.locator('.message').count()
        print(f"✅ Initial messages: {messages_count}")
        
        # Type a simple query
        test_query = "Hello, what courses do you have?"
        await page.fill("#chatInput", test_query)
        print(f"✅ Query typed: '{test_query}'")
        await page.screenshot(path="screenshot_3_query_typed.png")
        
        # Click send button
        await page.click("#sendButton")
        print("✅ Send button clicked")
        await page.screenshot(path="screenshot_4_after_send.png")
        
        # Wait a moment and check messages again
        await page.wait_for_timeout(3000)
        messages_after_send = await page.locator('.message').count()
        print(f"✅ Messages after 3 seconds: {messages_after_send}")
        await page.screenshot(path="screenshot_5_after_3_seconds.png")
        
        # Wait longer for response
        await page.wait_for_timeout(7000)  # Wait another 7 seconds (total 10)
        
        final_messages = await page.locator('.message').count()
        user_messages = await page.locator('.message.user').count()
        assistant_messages = await page.locator('.message.assistant').count()
        
        print(f"✅ Final state after 10 seconds:")
        print(f"   - Total messages: {final_messages}")
        print(f"   - User messages: {user_messages}")
        print(f"   - Assistant messages: {assistant_messages}")
        await page.screenshot(path="screenshot_6_final_state.png")
        
        # Get the text content of all messages
        print("\n📄 All messages content:")
        all_messages = page.locator('.message')
        count = await all_messages.count()
        for i in range(count):
            message = all_messages.nth(i)
            classes = await message.get_attribute('class')
            content = await message.text_content()
            print(f"   {i+1}. [{classes}]: {content[:100]}...")
        
        # Check network requests - look for any failed requests
        print("\n🔍 Checking for JavaScript errors or network issues...")
        
        await browser.close()
        
        print("\n📸 Screenshots saved:")
        print("   - screenshot_1_page_loaded.png")
        print("   - screenshot_2_chat_ready.png") 
        print("   - screenshot_3_query_typed.png")
        print("   - screenshot_4_after_send.png")
        print("   - screenshot_5_after_3_seconds.png")
        print("   - screenshot_6_final_state.png")

if __name__ == "__main__":
    asyncio.run(debug_with_screenshots())