#!/usr/bin/env python3
"""
Test script for multi-LLM RAG functionality with function calling
"""
import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from backend.rag_system import RAGSystem
from backend.ai_generator import AIGenerator
from backend.config import Config

async def test_rag_with_provider(provider_name: str, test_query: str):
    """Test RAG functionality with a specific provider"""
    print(f"\n{'='*60}")
    print(f"Testing RAG with {provider_name.upper()}")
    print(f"{'='*60}")
    
    try:
        # Initialize RAG system
        config = Config()
        rag_system = RAGSystem(config)
        
        # Load documents
        docs_path = Path(__file__).parent / "docs"
        if docs_path.exists():
            courses_added, chunks_added = rag_system.add_course_folder(str(docs_path))
            print(f"Loaded {courses_added} courses with {chunks_added} chunks")
        else:
            print("Warning: docs folder not found")
            return False
        
        # Test query
        print(f"\nQuery: {test_query}")
        print("-" * 40)
        
        response, sources = rag_system.query(test_query)
        
        print(f"Response: {response}")
        print(f"\nSources: {sources}")
        print(f"Provider used: {rag_system.ai_generator.provider_mode}")
        print(f"Model used: {rag_system.ai_generator.model}")
        
        return True
        
    except Exception as e:
        print(f"Error testing {provider_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    test_query = "What is MCP and how does it work?"
    
    # Test with OpenAI (current configuration)
    print("Testing with current configuration (OpenAI via AISuite)...")
    success_openai = await test_rag_with_provider("OpenAI", test_query)
    
    # Test with Anthropic by temporarily modifying environment
    print("\n" + "="*60)
    print("Switching to Anthropic for comparison...")
    print("="*60)
    
    # Temporarily remove OpenAI key to force Anthropic usage
    original_openai_key = os.environ.get('OPENAI_API_KEY')
    if original_openai_key:
        del os.environ['OPENAI_API_KEY']
    
    try:
        success_anthropic = await test_rag_with_provider("Anthropic", test_query)
    finally:
        # Restore OpenAI key
        if original_openai_key:
            os.environ['OPENAI_API_KEY'] = original_openai_key
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"OpenAI (AISuite): {'✓ PASS' if success_openai else '✗ FAIL'}")
    print(f"Anthropic: {'✓ PASS' if success_anthropic else '✗ FAIL'}")
    
    if success_openai and success_anthropic:
        print("\n🎉 Multi-LLM RAG functionality working correctly!")
        return True
    else:
        print("\n❌ Some providers failed. Check logs above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
