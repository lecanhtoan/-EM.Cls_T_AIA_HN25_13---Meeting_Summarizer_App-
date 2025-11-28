#!/usr/bin/env python3
"""
Script to interactively create .env file for Meeting Notes Summarizer

Usage:
    python create_env.py
"""

import os
import sys
from pathlib import Path


def get_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default value."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    value = input(full_prompt).strip()
    return value if value else default


def create_env_file():
    """Interactively create .env file."""
    
    print("\n" + "="*70)
    print("Meeting Notes Summarizer - Environment Setup")
    print("="*70 + "\n")
    
    # Check if .env already exists
    env_path = Path(".env")
    if env_path.exists():
        response = input(".env file already exists. Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return False
    
    print("\n" + "-"*70)
    print("AZURE OPENAI CONFIGURATION")
    print("-"*70)
    print("Get these from Azure Portal: https://portal.azure.com/\n")
    
    api_key = get_input("Azure OpenAI API Key")
    if not api_key:
        print("❌ API Key is required!")
        return False
    
    endpoint = get_input(
        "Azure OpenAI Endpoint (e.g., https://resource.openai.azure.com/)",
        "https://your-resource.openai.azure.com/"
    )
    if not endpoint.endswith('/'):
        endpoint += '/'
    
    deployment = get_input(
        "Azure OpenAI Deployment Name (e.g., gpt-4)",
        "gpt-4"
    )
    
    api_version = get_input(
        "Azure OpenAI API Version",
        "2024-08-01-preview"
    )
    
    print("\n" + "-"*70)
    print("POSTGRESQL CONFIGURATION")
    print("-"*70)
    print("Format: postgresql://username:password@host:port/database\n")
    
    db_user = get_input("PostgreSQL Username", "postgres")
    db_password = get_input("PostgreSQL Password", "password")
    db_host = get_input("PostgreSQL Host", "localhost")
    db_port = get_input("PostgreSQL Port", "5432")
    db_name = get_input("PostgreSQL Database Name", "meeting_notes_summarizer")
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print("\n" + "-"*70)
    print("APPLICATION SETTINGS")
    print("-"*70 + "\n")
    
    environment = get_input("Environment (development/production)", "development")
    debug = get_input("Debug Mode (true/false)", "true")
    secret_key = get_input(
        "Secret Key",
        "dev-secret-key-change-in-production"
    )
    frontend_url = get_input("Frontend URL", "http://localhost:5173")
    
    # Create .env content
    env_content = f"""# Azure OpenAI Configuration
# Get these from Azure Portal: https://portal.azure.com/
AZURE_OPENAI_API_KEY={api_key}
AZURE_OPENAI_ENDPOINT={endpoint}
AZURE_OPENAI_DEPLOYMENT_NAME={deployment}
AZURE_OPENAI_API_VERSION={api_version}

# PostgreSQL Configuration
# Format: postgresql://username:password@host:port/database
DATABASE_URL={database_url}

# Application Settings
ENVIRONMENT={environment}
DEBUG={debug}
SECRET_KEY={secret_key}

# Frontend URL (for CORS)
FRONTEND_URL={frontend_url}
"""
    
    # Write .env file
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print("\n" + "="*70)
        print("✅ .env file created successfully!")
        print("="*70)
        print(f"\nFile location: {env_path.absolute()}")
        print("\nConfiguration summary:")
        print(f"  Azure OpenAI API Key: {api_key[:10]}...")
        print(f"  Azure OpenAI Endpoint: {endpoint}")
        print(f"  Azure OpenAI Deployment: {deployment}")
        print(f"  PostgreSQL Database: {database_url.split('@')[1]}")
        print(f"  Environment: {environment}")
        print(f"  Frontend URL: {frontend_url}")
        
        print("\n" + "-"*70)
        print("NEXT STEPS")
        print("-"*70)
        print("\n1. Initialize database:")
        print("   python setup_db.py")
        print("\n2. Start backend server:")
        print("   python -m uvicorn app.main:app --reload")
        print("\n3. In another terminal, start frontend:")
        print("   cd ../frontend")
        print("   npm run dev")
        print("\n4. Open application:")
        print("   Frontend: http://localhost:5173")
        print("   API Docs: http://localhost:8000/docs")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error creating .env file: {e}")
        return False


def main():
    """Main entry point."""
    try:
        success = create_env_file()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


