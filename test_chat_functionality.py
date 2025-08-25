#!/usr/bin/env python3
"""
Test chat functionality to verify rate limiting fix
"""
import asyncio
from playwright.async_api import async_playwright

async def test_chat_functionality():
    print("🧪 Testing Chat Functionality After Rate Limit Fix...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to the app
        await page.goto("http://127.0.0.1:8000")
        print("✅ Page loaded")
        
        # Wait for page to be ready
        await page.wait_for_selector("#chatInput", timeout=10000)
        print("✅ Chat input ready")
        
        # Type a simple query
        test_query = "Hello, what courses do you have?"
        await page.fill("#chatInput", test_query)
        print(f"✅ Query typed: '{test_query}'")
        
        # Click send button
        await page.click("#sendButton")
        print("✅ Send button clicked")
        
        # Wait for response with increased timeout
        try:
            await page.wait_for_selector(".message.assistant:not(.welcome-message)", timeout=30000)
            print("✅ Assistant response received!")
            
            # Get the response text
            response_text = await page.locator('.message.assistant:not(.welcome-message)').last.text_content()
            print(f"✅ Response: {response_text[:100]}...")
            
            # Check that user message also appears
            user_messages = await page.locator('.message.user').count()
            assistant_messages = await page.locator('.message.assistant:not(.welcome-message)').count()
            
            print(f"✅ User messages: {user_messages}")
            print(f"✅ Assistant messages: {assistant_messages}")
            
            if user_messages >= 1 and assistant_messages >= 1:
                print("🎉 CHAT FUNCTIONALITY WORKING!")
                print("🔧 Rate limiting fix successful - chat is usable again")
            else:
                print("⚠️ Chat messages not appearing as expected")
                
        except Exception as e:
            print(f"❌ Chat response timeout or error: {e}")
            print("🔍 This might indicate the rate limiting is still too restrictive")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_chat_functionality())