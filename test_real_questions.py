#!/usr/bin/env python3
"""
Test chat functionality with real questions that should trigger RAG retrieval
"""
import asyncio
from playwright.async_api import async_playwright

async def test_real_questions():
    print("🧪 Testing Chat with Real Course Questions...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"🖥️ CONSOLE: {msg.text}"))
        page.on("pageerror", lambda msg: print(f"❌ PAGE ERROR: {msg}"))
        
        # Navigate to the app
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_selector("#chatInput", timeout=10000)
        print("✅ Page loaded and ready")
        
        # Test questions that should retrieve information from course materials
        test_questions = [
            "What is MCP and how does it work?",
            "Tell me about vector search and retrieval",
            "What are the key concepts in prompt compression?",
            "How do you build computer use applications?"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n📝 Question {i}: {question}")
            
            # Clear input and type question
            await page.fill("#chatInput", "")
            await page.fill("#chatInput", question)
            
            # Take screenshot before sending
            await page.screenshot(path=f"question_{i}_before.png")
            
            # Send the message
            await page.click("#sendButton")
            
            # Wait for response (longer timeout for AI processing)
            try:
                await page.wait_for_selector(".message.assistant:not(.welcome-message)", timeout=45000)
                
                # Wait a bit more for the response to fully load
                await page.wait_for_timeout(3000)
                
                # Take screenshot after response
                await page.screenshot(path=f"question_{i}_response.png")
                
                # Get the latest assistant response
                assistant_messages = page.locator(".message.assistant:not(.welcome-message)")
                latest_response = assistant_messages.last
                response_text = await latest_response.text_content()
                
                # Check for sources
                sources_element = latest_response.locator(".sources-collapsible")
                has_sources = await sources_element.count() > 0
                
                print(f"   ✅ Response received: {response_text[:150]}...")
                print(f"   📚 Has sources: {has_sources}")
                
                if has_sources:
                    # Click to expand sources
                    await sources_element.locator("summary").click()
                    await page.wait_for_timeout(1000)
                    sources_text = await sources_element.locator(".sources-content").text_content()
                    print(f"   📖 Sources: {sources_text}")
                
                # Take final screenshot with expanded sources
                await page.screenshot(path=f"question_{i}_final.png")
                
                print(f"   📸 Screenshots saved: question_{i}_before.png, question_{i}_response.png, question_{i}_final.png")
                
            except Exception as e:
                print(f"   ❌ Error or timeout: {e}")
                await page.screenshot(path=f"question_{i}_error.png")
                continue
            
            # Wait between questions
            await page.wait_for_timeout(2000)
        
        await browser.close()
        
        print("\n" + "="*60)
        print("🎯 REAL QUESTION TESTING COMPLETE")
        print("="*60)
        print("Check the screenshots to see actual responses with:")
        print("  • Real course content retrieval")
        print("  • Markdown formatting")
        print("  • Source citations")
        print("  • Proper UI rendering")

if __name__ == "__main__":
    asyncio.run(test_real_questions())