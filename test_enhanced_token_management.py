#!/usr/bin/env python3
"""
Test script for Enhanced Token Management
Demonstrates automatic bearer and refresh token handling
"""

import sys
import time
from multi_thread_unified_search import DataverseSearchClient, EnhancedTokenManager

def test_enhanced_token_management():
    """Test the enhanced token management functionality"""
    print("🧪 Enhanced Token Management Test")
    print("=" * 50)
    
    try:
        # Initialize client with enhanced token management
        print("1. Initializing DataverseSearchClient with Enhanced Token Management...")
        client = DataverseSearchClient()
        print(f"   ✅ Client initialized successfully")
        print(f"   📊 Token manager: {type(client.token_manager).__name__}")
        print(f"   🔑 Current token length: {len(client.token)} characters")
        
        # Check token validity
        print("\n2. Checking token validity...")
        is_valid = client._is_token_valid()
        print(f"   {'✅' if is_valid else '❌'} Token valid: {is_valid}")
        
        # Test token cache
        print("\n3. Examining token cache...")
        token_cache = client.token_manager._token_cache
        has_access = bool(token_cache.get("access_token"))
        has_refresh = bool(token_cache.get("refresh_token"))
        expires_at = token_cache.get("expires_at")
        
        print(f"   🔑 Has access token: {has_access}")
        print(f"   🔄 Has refresh token: {has_refresh}")
        print(f"   ⏰ Expires at: {expires_at}")
        
        # Test proactive token refresh check
        print("\n4. Testing proactive token refresh...")
        refresh_result = client._check_and_refresh_token_if_needed()
        print(f"   {'✅' if refresh_result else '❌'} Token refresh check: {refresh_result}")
        
        # Test force refresh capability (only if we have a refresh token)
        if has_refresh:
            print("\n5. Testing force refresh capability...")
            print("   ⚠️  This will force a token refresh using the stored refresh token")
            user_input = input("   Do you want to test force refresh? (y/N): ").lower().strip()
            
            if user_input == 'y':
                force_result = client.force_token_refresh()
                print(f"   {'✅' if force_result else '❌'} Force refresh result: {force_result}")
            else:
                print("   ⏭️  Skipping force refresh test")
        else:
            print("\n5. ⚠️  No refresh token available - cannot test force refresh")
        
        # Test a simple search to verify everything works
        print("\n6. Testing search functionality with managed tokens...")
        try:
            result = client.search("women's shoes", retry_count=0)
            search_success = result.get("success", False)
            product_count = len(result.get("api_response_products", {}).get("product_names_found", []))
            
            print(f"   {'✅' if search_success else '❌'} Search successful: {search_success}")
            print(f"   📦 Products found: {product_count}")
            
            if search_success:
                print("   🎉 Token management is working correctly with live API calls!")
            
        except Exception as e:
            print(f"   ❌ Search test failed: {e}")
        
        print("\n" + "=" * 50)
        print("🎯 Enhanced Token Management Summary:")
        print(f"   • Token validation: {'✅ Working' if is_valid else '❌ Failed'}")
        print(f"   • Access token: {'✅ Available' if has_access else '❌ Missing'}")
        print(f"   • Refresh token: {'✅ Available' if has_refresh else '❌ Missing'}")
        print(f"   • Automatic refresh: {'✅ Working' if refresh_result else '❌ Failed'}")
        print("   • Token files: enhanced_tokens.config, token.config (legacy)")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def demonstrate_token_manager_standalone():
    """Demonstrate the standalone EnhancedTokenManager functionality"""
    print("\n🔬 Standalone EnhancedTokenManager Demonstration")
    print("=" * 50)
    
    try:
        # Create standalone token manager
        token_manager = EnhancedTokenManager(
            tenant_id="4abc24ea-2d0b-4011-87d4-3de32ca1e9cc",
            client_id="51f81489-12ee-4a9e-aaae-a2591f45987d",
            resource_url="https://aurorabapenv87b96.crm10.dynamics.com/"
        )
        
        print("✅ Standalone EnhancedTokenManager created")
        
        # Get valid access token
        token_result = token_manager.get_valid_access_token()
        print(f"{'✅' if token_result['success'] else '❌'} Token acquisition: {token_result['success']}")
        print(f"   Method used: {token_result.get('method', 'unknown')}")
        
        if token_result['success']:
            token_length = len(token_result['access_token'])
            print(f"   Token length: {token_length} characters")
        
        # Show token cache status
        cache = token_manager._token_cache
        print(f"   Cache status:")
        print(f"     - Access token: {'✅' if cache.get('access_token') else '❌'}")
        print(f"     - Refresh token: {'✅' if cache.get('refresh_token') else '❌'}")
        print(f"     - Expires at: {cache.get('expires_at', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Standalone test failed: {e}")

if __name__ == "__main__":
    print("🚀 Enhanced Token Management Test Suite")
    print("This script tests the new Bearer + Refresh token management system")
    print()
    
    # Run main test
    test_enhanced_token_management()
    
    # Run standalone demonstration
    demonstrate_token_manager_standalone()
    
    print("\n✨ Test completed!")
