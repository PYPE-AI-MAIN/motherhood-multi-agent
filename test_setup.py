#!/usr/bin/env python3
"""
Test script to verify Felix Hospital agent setup
Run this to check if everything is configured correctly
"""

import sys
import os

def check_python_version():
    """Check Python version"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.9+)")
        return False

def check_env_file():
    """Check if .env file exists"""
    print("\nChecking .env file...")
    if os.path.exists(".env"):
        print("✅ .env file exists")
        return True
    else:
        print("❌ .env file not found")
        print("   Run: cp .env.example .env")
        return False

def check_imports():
    """Check if required packages are installed"""
    print("\nChecking required packages...")
    required = [
        "livekit",
        "openai",
        "pydantic",
        "dotenv",
        "structlog"
    ]
    
    all_ok = True
    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} not installed")
            all_ok = False
    
    if not all_ok:
        print("\n   Run: pip install -r requirements.txt")
    
    return all_ok

def check_env_variables():
    """Check environment variables"""
    print("\nChecking environment variables...")
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY"
    ]
    
    all_ok = True
    for var in required_vars:
        value = os.getenv(var)
        if value and value != f"your_{var.lower().replace('_', '-')}":
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} not configured")
            all_ok = False
    
    if not all_ok:
        print("\n   Edit .env file with your credentials")
    
    return all_ok

def test_mock_api():
    """Test mock API"""
    print("\nTesting Mock Felix Hospital API...")
    try:
        from src.tools.felix_api import felix_api
        import asyncio
        
        async def test():
            # Search doctors
            doctors = await felix_api.search_doctors("14")  # Cardiology
            if doctors:
                print(f"✅ Found {len(doctors)} Cardiology doctors")
                
                # Get slots
                doctor = doctors[0]
                from src.utils.date_helpers import get_today, add_days
                slots = await felix_api.get_doctor_slots(
                    doctor['doctor_id'],
                    get_today(),
                    add_days(get_today(), 2)
                )
                if slots:
                    print(f"✅ Found {len(slots)} available slots")
                    return True
            return False
        
        result = asyncio.run(test())
        return result
    except Exception as e:
        print(f"❌ Error testing mock API: {e}")
        return False

def main():
    """Run all checks"""
    print("="*50)
    print("Felix Hospital Agent - Setup Verification")
    print("="*50)
    
    checks = [
        check_python_version(),
        check_env_file(),
        check_imports(),
        check_env_variables(),
        test_mock_api()
    ]
    
    print("\n" + "="*50)
    if all(checks):
        print("✅ ALL CHECKS PASSED!")
        print("\nYou can now run the agent:")
        print("  python src/main.py dev")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before running the agent.")
    print("="*50)

if __name__ == "__main__":
    main()
