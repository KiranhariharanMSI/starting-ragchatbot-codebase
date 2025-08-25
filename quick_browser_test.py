#!/usr/bin/env python3
"""
Quick browser test to verify functionality
"""
import asyncio
from playwright.async_api import async_playwright

async def quick_test():
    print("🧪 Quick Browser Test Starting...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("📄 Testing page load...")
        await page.goto("http://127.0.0.1:8000")
        
        # Check title
        title = await page.title()
        print(f"   Page title: {title}")
        assert "Course Materials Assistant" in title
        
        # Check main heading
        heading = await page.locator("h1").text_content()
        print(f"   Main heading: {heading}")
        
        # Check course stats loading
        print("📊 Testing course stats...")
        # Wait for page to load then check if element exists
        await page.wait_for_timeout(3000)  # Give time for JS to load
        
        # Check if element exists and get text even if hidden
        total_courses_elem = page.locator("#totalCourses")
        if await total_courses_elem.count() > 0:
            total_courses = await total_courses_elem.text_content()
            print(f"   Total courses: {total_courses}")
        else:
            print("   ⚠️  Total courses element not found, checking API directly...")
            # Test API endpoint directly
            response = await page.goto("http://127.0.0.1:8000/api/courses")
            if response.status == 200:
                print("   ✅ Course API working")
        
        # Go back to main page for chat testing
        await page.goto("http://127.0.0.1:8000")
        
        # Check chat interface
        print("💬 Testing chat interface...")
        chat_input = page.locator("#chatInput")
        send_button = page.locator("#sendButton")
        assert await chat_input.is_visible()
        assert await send_button.is_visible()
        print("   Chat elements visible")
        
        # Test a simple query
        print("🔍 Testing query functionality...")
        await page.fill("#chatInput", "What courses do you have?")
        await page.click("#sendButton")
        
        # Wait for response
        await page.wait_for_selector(".message.assistant:not(.welcome-message)", timeout=30000)
        
        # Check response
        response = await page.locator('.message.assistant:not(.welcome-message)').last.text_content()
        print(f"   Response received: {response[:100]}...")
        
        # Test security headers
        print("🔒 Testing security headers...")
        response = await page.goto("http://127.0.0.1:8000/health")
        headers = response.headers
        
        security_headers = ['x-content-type-options', 'x-frame-options', 'content-security-policy']
        for header in security_headers:
            assert header in headers, f"Missing {header}"
        print("   Security headers present")
        
        await browser.close()
        print("✅ All quick tests passed!")

if __name__ == "__main__":
    asyncio.run(quick_test())