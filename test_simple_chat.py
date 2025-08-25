#!/usr/bin/env python3
"""
Simple test to see what's happening with the frontend response handling
"""
import asyncio
from playwright.async_api import async_playwright

async def test_simple_chat():
    print("🔍 Testing Simple Chat Response...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable all logging
        page.on("console", lambda msg: print(f"🖥️ CONSOLE {msg.type}: {msg.text}"))
        page.on("pageerror", lambda msg: print(f"❌ PAGE ERROR: {msg}"))
        page.on("request", lambda req: print(f"🌐 REQUEST: {req.method} {req.url}"))
        page.on("response", lambda res: print(f"📡 RESPONSE: {res.status} {res.url}"))
        
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_selector("#chatInput", timeout=10000)
        
        print("\n📝 Asking: 'What is MCP?'")
        await page.fill("#chatInput", "What is MCP?")
        await page.screenshot(path="before_send.png")
        
        # Monitor network traffic
        page.on("response", lambda response: print(f"📡 Response {response.status}: {response.url}"))
        
        await page.click("#sendButton")
        print("✅ Send button clicked")
        
        # Wait and take screenshots to see what happens
        await page.wait_for_timeout(2000)
        await page.screenshot(path="after_2_seconds.png")
        print("📸 Screenshot after 2 seconds")
        
        await page.wait_for_timeout(3000)
        await page.screenshot(path="after_5_seconds.png")
        print("📸 Screenshot after 5 seconds")
        
        await page.wait_for_timeout(5000)
        await page.screenshot(path="after_10_seconds.png")
        print("📸 Screenshot after 10 seconds")
        
        # Check final state
        messages = await page.locator('.message').count()
        user_messages = await page.locator('.message.user').count()
        assistant_messages = await page.locator('.message.assistant:not(.welcome-message)').count()
        loading_messages = await page.locator('.loading').count()
        
        print(f"\n📊 Final State:")
        print(f"   Total messages: {messages}")
        print(f"   User messages: {user_messages}")
        print(f"   Assistant messages: {assistant_messages}")
        print(f"   Loading indicators: {loading_messages}")
        
        if assistant_messages > 0:
            response_text = await page.locator('.message.assistant:not(.welcome-message)').last.inner_text()
            print(f"   📝 Response text: {response_text[:200]}...")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_simple_chat())