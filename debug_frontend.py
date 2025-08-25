#!/usr/bin/env python3
"""
Debug frontend chat functionality to see what's happening
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_frontend():
    print("🔍 Debugging Frontend Chat Functionality...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Run with GUI to see what's happening
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"🖥️ CONSOLE: {msg.text}"))
        page.on("pageerror", lambda msg: print(f"❌ PAGE ERROR: {msg}"))
        
        # Navigate to the app
        await page.goto("http://127.0.0.1:8000")
        print("✅ Page loaded")
        
        # Wait for page to be ready
        await page.wait_for_selector("#chatInput", timeout=10000)
        print("✅ Chat input ready")
        
        # Check initial state
        messages_count = await page.locator('.message').count()
        print(f"✅ Initial messages: {messages_count}")
        
        # Type a simple query
        test_query = "Hello, what courses do you have?"
        await page.fill("#chatInput", test_query)
        print(f"✅ Query typed: '{test_query}'")
        
        # Check if send button is enabled
        send_button_disabled = await page.locator("#sendButton").is_disabled()
        print(f"✅ Send button disabled: {send_button_disabled}")
        
        # Click send button
        await page.click("#sendButton")
        print("✅ Send button clicked")
        
        # Wait a moment and check messages again
        await page.wait_for_timeout(2000)
        messages_after_send = await page.locator('.message').count()
        print(f"✅ Messages after send: {messages_after_send}")
        
        # Check for loading indicator
        loading_count = await page.locator('.loading').count()
        print(f"✅ Loading indicators: {loading_count}")
        
        # Wait for response and check final state
        await page.wait_for_timeout(10000)  # Wait 10 seconds
        
        final_messages = await page.locator('.message').count()
        user_messages = await page.locator('.message.user').count()
        assistant_messages = await page.locator('.message.assistant').count()
        
        print(f"✅ Final state:")
        print(f"   - Total messages: {final_messages}")
        print(f"   - User messages: {user_messages}")
        print(f"   - Assistant messages: {assistant_messages}")
        
        # Check if there are any error messages
        error_elements = await page.locator('.error').count()
        print(f"   - Error elements: {error_elements}")
        
        # Get the text content of all messages
        print("\n📄 All messages content:")
        all_messages = page.locator('.message')
        count = await all_messages.count()
        for i in range(count):
            message = all_messages.nth(i)
            classes = await message.get_attribute('class')
            content = await message.text_content()
            print(f"   {i+1}. [{classes}]: {content[:100]}...")
        
        input("Press Enter to close browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_frontend())