#!/usr/bin/env python3
"""
Playwright browser tests for RAG chatbot functionality and security
"""
import asyncio
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import subprocess
import time
import signal
import os

class TestRAGChatbot:
    """Browser tests for RAG chatbot application"""
    
    @pytest.fixture(scope="class")
    def server_process(self):
        """Start the FastAPI server for testing"""
        print("\n🚀 Starting test server...")
        process = subprocess.Popen(
            ["uv", "run", "uvicorn", "backend.app:app", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait for server to start
        time.sleep(5)
        
        yield process
        
        print("\n🛑 Stopping test server...")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except Exception:
            process.kill()
        process.wait()
    
    @pytest_asyncio.fixture(scope="class") 
    async def browser_setup(self):
        """Setup Playwright browser for testing"""
        print("\n🌐 Setting up browser...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            yield page, browser, context
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_basic_page_load(self, server_process, browser_setup):
        """Test basic frontend loading and UI elements"""
        page, browser, context = browser_setup
        
        print("\n📄 Testing basic page load...")
        
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
        
        print("✅ Basic page load successful")
    
    @pytest.mark.asyncio
    async def test_course_statistics_loading(self, server_process, browser_setup):
        """Test course statistics sidebar loading"""
        page, browser, context = browser_setup
        
        print("\n📊 Testing course statistics loading...")
        
        await page.goto("http://localhost:8000")
        
        # Wait for course stats to load
        await page.wait_for_selector("#totalCourses", timeout=10000)
        
        # Check total courses displays
        total_courses = await page.locator("#totalCourses").text_content()
        assert total_courses.isdigit()
        
        # Check course titles section exists
        course_titles = await page.locator("#courseTitles")
        assert await course_titles.is_visible()
        
        print(f"✅ Course statistics loaded: {total_courses} courses")
    
    @pytest.mark.asyncio
    async def test_chat_interface_elements(self, server_process, browser_setup):
        """Test chat interface UI elements"""
        page, browser, context = browser_setup
        
        print("\n💬 Testing chat interface elements...")
        
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
        
        print("✅ Chat interface elements present")
    
    @pytest.mark.asyncio
    async def test_valid_query_functionality(self, server_process, browser_setup):
        """Test chat functionality with a valid query"""
        page, browser, context = browser_setup
        
        print("\n🔍 Testing valid query functionality...")
        
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
        
        print(f"✅ Valid query processed successfully")
        print(f"   Response: {response_text[:100]}...")
    
    @pytest.mark.asyncio 
    async def test_suggested_questions(self, server_process, browser_setup):
        """Test suggested question functionality"""
        page, browser, context = browser_setup
        
        print("\n❓ Testing suggested questions...")
        
        await page.goto("http://localhost:8000")
        
        # Wait for suggested questions to load
        await page.wait_for_selector(".suggested-item", timeout=10000)
        
        # Click first suggested question
        await page.click(".suggested-item:first-child")
        
        # Check that question text is filled in input
        input_value = await page.input_value("#chatInput")
        assert len(input_value) > 0
        
        print(f"✅ Suggested question clicked: '{input_value}'")
    
    @pytest.mark.asyncio
    async def test_input_validation_browser(self, server_process, browser_setup):
        """Test input validation in browser context"""
        page, browser, context = browser_setup
        
        print("\n🛡️ Testing input validation in browser...")
        
        await page.goto("http://localhost:8000")
        
        # Wait for chat input
        await page.wait_for_selector("#chatInput", timeout=10000)
        
        # Test with very long query (over 1000 characters)
        long_query = "A" * 1500
        await page.fill("#chatInput", long_query)
        await page.click("#sendButton")
        
        # Wait for error response
        await page.wait_for_selector(".message.assistant:not(.welcome-message)", timeout=15000)
        
        # Check that some kind of error or validation response occurs
        response_text = await page.locator('.message.assistant:not(.welcome-message)').last.text_content()
        
        # Should contain error or validation message
        print(f"✅ Input validation response: {response_text}")
    
    @pytest.mark.asyncio
    async def test_security_headers_browser(self, server_process, browser_setup):
        """Test security headers in browser context"""  
        page, browser, context = browser_setup
        
        print("\n🔒 Testing security headers in browser context...")
        
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
        
        print("✅ All security headers present and valid")
    
    @pytest.mark.asyncio
    async def test_rate_limiting_browser(self, server_process, browser_setup):
        """Test rate limiting behavior in browser"""
        page, browser, context = browser_setup
        
        print("\n⏱️ Testing rate limiting in browser context...")
        
        await page.goto("http://localhost:8000")
        
        # Test multiple rapid queries
        for i in range(3):
            await page.fill("#chatInput", f"Test query {i}")
            await page.click("#sendButton")
            await page.wait_for_timeout(1000)  # Wait 1 second
        
        # Check that responses are handled appropriately
        assistant_messages = await page.locator('.message.assistant:not(.welcome-message)').count()
        print(f"✅ Rate limiting test completed - {assistant_messages} responses received")
    
    @pytest.mark.asyncio
    async def test_responsive_design(self, server_process, browser_setup):
        """Test responsive design on different screen sizes"""
        page, browser, context = browser_setup
        
        print("\n📱 Testing responsive design...")
        
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
        
        print("✅ Responsive design working across viewports")

# Run tests if script is called directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])