#!/usr/bin/env python3
"""
Simple Playwright browser tests for RAG chatbot functionality and security
"""
import asyncio
import subprocess
import time
import signal
import os
from playwright.async_api import async_playwright


async def start_server():
    """Start the FastAPI server for testing"""
    print("🚀 Starting test server...")
    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "backend.app:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    
    # Wait for server to start and check if it's ready
    print("⏳ Waiting for server to be ready...")
    for i in range(30):  # Try for up to 30 seconds
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8000/health", timeout=1)
            print(f"✅ Server ready after {i+1} seconds")
            break
        except:
            time.sleep(1)
    else:
        raise Exception("Server failed to start within 30 seconds")
    
    return process


def stop_server(process):
    """Stop the test server"""
    print("🛑 Stopping test server...")
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except Exception:
        process.kill()
    process.wait()


async def test_basic_page_load():
    """Test basic frontend loading and UI elements"""
    print("\n📄 Testing basic page load...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the app
        await page.goto("http://localhost:8000")
        
        # Check page title
        title = await page.title()
        assert "Course Materials Assistant" in title
        
        # Check main heading
        heading = await page.locator("h1").text_content()
        assert "Course Materials Assistant" in heading
        
        # Check subtitle
        subtitle = await page.locator(".subtitle").text_content()
        assert "Ask questions about courses" in subtitle
        
        await browser.close()
        print("✅ Basic page load successful")


async def test_course_statistics_loading():
    """Test course statistics sidebar loading"""
    print("\n📊 Testing course statistics loading...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("http://localhost:8000")
        
        # Wait for course stats to load
        await page.wait_for_selector("#totalCourses", timeout=10000)
        
        # Check total courses displays
        total_courses = await page.locator("#totalCourses").text_content()
        assert total_courses.isdigit()
        
        # Check course titles section exists
        course_titles = await page.locator("#courseTitles")
        assert await course_titles.is_visible()
        
        await browser.close()
        print(f"✅ Course statistics loaded: {total_courses} courses")


async def test_chat_interface_elements():
    """Test chat interface UI elements"""
    print("\n💬 Testing chat interface elements...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("http://localhost:8000")
        
        # Check chat messages container
        chat_messages = await page.locator("#chatMessages")
        assert await chat_messages.is_visible()
        
        # Check welcome message
        welcome_msg = await page.locator(".welcome-message").text_content()
        assert "Welcome to the Course Materials Assistant" in welcome_msg
        
        # Check chat input
        chat_input = await page.locator("#chatInput")
        assert await chat_input.is_visible()
        
        # Check send button
        send_button = await page.locator("#sendButton")
        assert await send_button.is_visible()
        
        # Check suggested questions
        suggested_questions = await page.locator(".suggested-item").count()
        assert suggested_questions > 0
        
        await browser.close()
        print("✅ Chat interface elements present")


async def test_valid_query_functionality():
    """Test chat functionality with a valid query"""
    print("\n🔍 Testing valid query functionality...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("http://localhost:8000")
        
        # Wait for page to load
        await page.wait_for_selector("#chatInput", timeout=10000)
        
        # Type a query
        test_query = "What courses are available?"
        await page.fill("#chatInput", test_query)
        
        # Click send button
        await page.click("#sendButton")
        
        # Wait for response (with increased timeout for AI processing)
        await page.wait_for_selector(".message.assistant:not(.welcome-message)", timeout=30000)
        
        # Check user message appears
        user_messages = await page.locator('.message.user').count()
        assert user_messages >= 1
        
        # Check assistant response appears
        assistant_messages = await page.locator('.message.assistant:not(.welcome-message)').count()
        assert assistant_messages >= 1
        
        # Get the response text
        response_text = await page.locator('.message.assistant:not(.welcome-message)').last.text_content()
        assert len(response_text) > 0
        
        await browser.close()
        print(f"✅ Valid query processed successfully")
        print(f"   Response: {response_text[:100]}...")


async def test_suggested_questions():
    """Test suggested question functionality"""
    print("\n❓ Testing suggested questions...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("http://localhost:8000")
        
        # Wait for suggested questions to load
        await page.wait_for_selector(".suggested-item", timeout=10000)
        
        # Click first suggested question
        await page.click(".suggested-item:first-child")
        
        # Check that question text is filled in input
        input_value = await page.input_value("#chatInput")
        assert len(input_value) > 0
        
        await browser.close()
        print(f"✅ Suggested question clicked: '{input_value}'")


async def test_security_headers_browser():
    """Test security headers in browser context"""  
    print("\n🔒 Testing security headers in browser context...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate and capture response
        response = await page.goto("http://localhost:8000")
        
        # Check response headers
        headers = response.headers
        
        security_headers = {
            'x-content-type-options': 'nosniff',
            'x-frame-options': 'DENY', 
            'x-xss-protection': '1; mode=block',
            'referrer-policy': 'strict-origin-when-cross-origin',
            'content-security-policy': 'default-src',  # Partial match
            'strict-transport-security': 'max-age'     # Partial match
        }
        
        for header, expected in security_headers.items():
            assert header in headers, f"Missing security header: {header}"
            assert expected in headers[header], f"Invalid {header}: {headers[header]}"
        
        await browser.close()
        print("✅ All security headers present and valid")


async def test_responsive_design():
    """Test responsive design on different screen sizes"""
    print("\n📱 Testing responsive design...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Test mobile viewport
        await page.set_viewport_size({"width": 375, "height": 667})
        await page.goto("http://localhost:8000")
        
        # Check elements are still visible
        assert await page.locator("#chatInput").is_visible()
        assert await page.locator("#sendButton").is_visible()
        
        # Test tablet viewport
        await page.set_viewport_size({"width": 768, "height": 1024})
        await page.reload()
        
        assert await page.locator(".container").is_visible()
        
        # Test desktop viewport
        await page.set_viewport_size({"width": 1920, "height": 1080})
        await page.reload()
        
        assert await page.locator(".sidebar").is_visible()
        
        await browser.close()
        print("✅ Responsive design working across viewports")


async def run_all_tests():
    """Run all browser tests with server management"""
    server_process = None
    
    try:
        # Start server
        server_process = await start_server()
        
        # Run all tests
        print("\n🧪 Running Browser Functionality Tests\n" + "="*50)
        
        await test_basic_page_load()
        await test_course_statistics_loading()
        await test_chat_interface_elements()
        await test_valid_query_functionality()
        await test_suggested_questions()
        await test_security_headers_browser()
        await test_responsive_design()
        
        print("\n" + "="*50)
        print("🎉 All browser tests passed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise
    finally:
        if server_process:
            stop_server(server_process)


# Run tests if script is called directly
if __name__ == "__main__":
    asyncio.run(run_all_tests())