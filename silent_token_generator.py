#!/usr/bin/env python3
"""
Silent Token Generator for Dataverse API
Implements silent token acquisition without browser interaction
Based on Insomnia OAuth2 configuration provided
"""

import json
import requests
import base64
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
import os

class SilentTokenGenerator:
    """Generates tokens silently using various OAuth2 flows"""
    
    def __init__(self):
        # Configuration based on Insomnia setup
        self.tenant_id = "4abc24ea-2d0b-4011-87d4-3de32ca1e9cc"  # From current token
        self.client_id = "51f81489-12ee-4a9e-aaae-a2591f45987d"  # Fixed Copilot team ID
        
        # Multiple endpoint configurations (from your docs vs current token)
        self.endpoints = {
            "insomnia_config": "https://org07b6556d.crm.dynamics.com",
            "current_token": "https://aurorabapenv87b96.crm10.dynamics.com"
        }
        
        # OAuth2 endpoints
        self.token_endpoint = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.device_code_endpoint = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/devicecode"
        
        # Credentials storage
        self.credentials_file = "stored_credentials.json"
        self.refresh_token_file = "refresh_token.config"
        
    def load_stored_credentials(self):
        """Load previously stored credentials"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"⚠️ Error loading stored credentials: {e}")
            return None
    
    def save_credentials(self, credentials):
        """Save credentials for future use"""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            print(f"✅ Credentials saved to {self.credentials_file}")
        except Exception as e:
            print(f"❌ Error saving credentials: {e}")
    
    def load_refresh_token(self):
        """Load refresh token if available"""
        try:
            if os.path.exists(self.refresh_token_file):
                with open(self.refresh_token_file, 'r') as f:
                    return f.read().strip()
            return None
        except Exception as e:
            print(f"⚠️ Error loading refresh token: {e}")
            return None
    
    def save_refresh_token(self, refresh_token):
        """Save refresh token for future use"""
        try:
            with open(self.refresh_token_file, 'w') as f:
                f.write(refresh_token)
            print(f"✅ Refresh token saved to {self.refresh_token_file}")
        except Exception as e:
            print(f"❌ Error saving refresh token: {e}")
    
    def get_token_with_refresh_token(self, refresh_token, resource_url):
        """Get access token using refresh token"""
        print("🔄 Attempting token refresh with stored refresh token...")
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'refresh_token': refresh_token,
            'resource': resource_url,
            'scope': 'user_impersonation'
        }
        
        try:
            response = requests.post(self.token_endpoint, data=data, timeout=30)
            response.raise_for_status()
            
            token_response = response.json()
            
            # Save new refresh token if provided
            if 'refresh_token' in token_response:
                self.save_refresh_token(token_response['refresh_token'])
            
            return {
                'success': True,
                'access_token': token_response['access_token'],
                'refresh_token': token_response.get('refresh_token'),
                'expires_in': token_response.get('expires_in', 3600),
                'method': 'refresh_token'
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Refresh token request failed: {str(e)}",
                'method': 'refresh_token'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Refresh token processing failed: {str(e)}",
                'method': 'refresh_token'
            }
    
    def get_token_with_device_code(self, resource_url):
        """Get token using device code flow (user-friendly silent method)"""
        print("🔄 Initiating device code authentication flow...")
        
        # Step 1: Request device code
        device_data = {
            'client_id': self.client_id,
            'resource': resource_url,
            'scope': 'user_impersonation'
        }
        
        try:
            device_response = requests.post(self.device_code_endpoint, data=device_data, timeout=30)
            device_response.raise_for_status()
            device_result = device_response.json()
            
            print(f"📱 Device Code Authentication Required:")
            print(f"   1. Open: {device_result['verification_uri']}")
            print(f"   2. Enter code: {device_result['user_code']}")
            print(f"   3. Complete authentication in browser")
            print(f"   4. Waiting for completion... ({device_result.get('expires_in', 900)} seconds)")
            
            # Step 2: Poll for token
            token_data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'client_id': self.client_id,
                'device_code': device_result['device_code']
            }
            
            interval = device_result.get('interval', 5)
            expires_in = device_result.get('expires_in', 900)
            start_time = time.time()
            
            while time.time() - start_time < expires_in:
                try:
                    token_response = requests.post(self.token_endpoint, data=token_data, timeout=30)
                    
                    if token_response.status_code == 200:
                        token_result = token_response.json()
                        print("✅ Authentication completed successfully!")
                        
                        # Save refresh token if provided
                        if 'refresh_token' in token_result:
                            self.save_refresh_token(token_result['refresh_token'])
                        
                        return {
                            'success': True,
                            'access_token': token_result['access_token'],
                            'refresh_token': token_result.get('refresh_token'),
                            'expires_in': token_result.get('expires_in', 3600),
                            'method': 'device_code'
                        }
                    
                    elif token_response.status_code == 400:
                        error_data = token_response.json()
                        if error_data.get('error') == 'authorization_pending':
                            print(f"⏳ Waiting for user authentication... ({int((expires_in - (time.time() - start_time)) / 60)} min remaining)")
                            time.sleep(interval)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f"Device code error: {error_data.get('error_description', str(error_data))}",
                                'method': 'device_code'
                            }
                    else:
                        return {
                            'success': False,
                            'error': f"Unexpected response: {token_response.status_code} - {token_response.text}",
                            'method': 'device_code'
                        }
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Poll request failed, retrying: {e}")
                    time.sleep(interval)
                    continue
            
            return {
                'success': False,
                'error': "Device code authentication timed out",
                'method': 'device_code'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Device code flow failed: {str(e)}",
                'method': 'device_code'
            }
    
    def get_token_with_client_credentials(self, resource_url, client_secret=None):
        """Get token using client credentials flow (for service accounts)"""
        if not client_secret:
            return {
                'success': False,
                'error': "Client credentials flow requires client_secret",
                'method': 'client_credentials'
            }
        
        print("🔄 Attempting client credentials authentication...")
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': client_secret,
            'resource': resource_url
        }
        
        try:
            response = requests.post(self.token_endpoint, data=data, timeout=30)
            response.raise_for_status()
            
            token_response = response.json()
            
            return {
                'success': True,
                'access_token': token_response['access_token'],
                'expires_in': token_response.get('expires_in', 3600),
                'method': 'client_credentials'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Client credentials failed: {str(e)}",
                'method': 'client_credentials'
            }
    
    def acquire_token_silently(self, preferred_resource=None):
        """Main method to acquire token using available silent methods"""
        
        print("🚀 Silent Token Acquisition")
        print("=" * 40)
        
        # Determine resource URL
        resource_url = preferred_resource or self.endpoints["current_token"]
        print(f"🎯 Target resource: {resource_url}")
        
        # Method 1: Try refresh token
        refresh_token = self.load_refresh_token()
        if refresh_token:
            result = self.get_token_with_refresh_token(refresh_token, resource_url)
            if result['success']:
                return result
            else:
                print(f"⚠️ Refresh token failed: {result['error']}")
        
        # Method 2: Try stored credentials (if available)
        stored_creds = self.load_stored_credentials()
        if stored_creds and 'client_secret' in stored_creds:
            result = self.get_token_with_client_credentials(resource_url, stored_creds['client_secret'])
            if result['success']:
                return result
            else:
                print(f"⚠️ Client credentials failed: {result['error']}")
        
        # Method 3: Device code flow (user interaction required but minimal)
        print("📱 Falling back to device code authentication...")
        result = self.get_token_with_device_code(resource_url)
        return result
    
    def save_token_to_file(self, access_token, filename="token.config"):
        """Save access token to the token file"""
        try:
            with open(filename, 'w') as f:
                f.write(access_token)
            print(f"✅ Access token saved to {filename}")
            return True
        except Exception as e:
            print(f"❌ Error saving token to file: {e}")
            return False

def main():
    """Main execution function"""
    generator = SilentTokenGenerator()
    
    print("🎯 Silent Token Generator for Dataverse API")
    print("Based on Insomnia OAuth2 configuration")
    print("=" * 60)
    
    # Try both resource endpoints
    for endpoint_name, resource_url in generator.endpoints.items():
        print(f"\n🔄 Attempting token acquisition for {endpoint_name}: {resource_url}")
        
        result = generator.acquire_token_silently(resource_url)
        
        if result['success']:
            print(f"✅ Token acquired successfully using {result['method']} method!")
            print(f"   Token length: {len(result['access_token'])} characters")
            print(f"   Expires in: {result.get('expires_in', 'Unknown')} seconds")
            
            # Save token
            if generator.save_token_to_file(result['access_token']):
                print("🎉 Token saved and ready for use!")
                
                # Test token validity
                from multi_thread_runner import DataverseSearchClient
                try:
                    client = DataverseSearchClient()
                    if client._is_token_valid():
                        print("✅ Token validation passed!")
                    else:
                        print("⚠️ Token validation failed - may still work for API calls")
                except Exception as e:
                    print(f"ℹ️ Token validation test not available: {e}")
                
                return True
            else:
                print("❌ Failed to save token")
                return False
        else:
            print(f"❌ Token acquisition failed: {result['error']}")
    
    print("\n❌ All token acquisition methods failed")
    print("\n💡 Alternative options:")
    print("1. Use Insomnia to generate token manually and save to token.config")
    print("2. Check if client credentials or refresh tokens are available")
    print("3. Verify network connectivity and authentication parameters")
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Token generation cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)