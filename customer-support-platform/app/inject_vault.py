import os
import sys
from dotenv import load_dotenv
import hvac

# Sensitive keys that should be stored in Vault
SENSITIVE_KEYS = {
    'SECRET_KEY', 'ACCESS_TOKEN_EXPIRE_MINUTES', 'ALGORITHM',
    'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB',
    'REDIS_PASSWORD', 'RABBITMQ_USER', 'RABBITMQ_PASSWORD',
    'OPENAI_API_KEY', 'GROQ_API_KEY',
    'KEYCLOAK_CLIENT_SECRET', 'KEYCLOAK_ADMIN_CLIENT_SECRET', 'KEYCLOAK_ADMIN_PASSWORD',
    'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM_EMAIL',
    'TELEGRAM_BOT_TOKEN', 'RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET',
    'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY', 'SENTRY_DSN',
    'PGLADMIN_DEFAULT_PASSWORD', 'FLOWER_PASSWORD'
}

def get_vault_client():
    """Initialize Vault client."""
    vault_addr = os.getenv("VAULT_ADDR", "http://localhost:8200")
    vault_token = os.getenv("VAULT_TOKEN", os.getenv("VAULT_DEV_ROOT_TOKEN", "root-token"))
    
    client = hvac.Client(url=vault_addr, token=vault_token)
    
    if not client.is_authenticated():
        raise Exception(f"Failed to authenticate with Vault at {vault_addr}")
    
    return client

def get_secrets_from_env():
    """Extract sensitive environment variables."""
    secrets = {}
    
    # Get only explicitly defined sensitive keys
    for key in SENSITIVE_KEYS:
        value = os.getenv(key)
        if value and value.strip():
            secrets[key] = value
    
    return secrets

def main():
    print("Vault Secrets Injection")
    print("-" * 30)
    
    # Load .env file
    if not load_dotenv():
        print("Error: Could not load .env file")
        return False
    
    print("Loaded .env file")
    
    try:
        # Connect to Vault
        client = get_vault_client()
        print("Connected to Vault")
        
        # Get secrets
        secrets = get_secrets_from_env()
        if not secrets:
            print("Warning: No secrets found")
            return False
        
        print(f"Found {len(secrets)} secrets")
        
        # Store in Vault
        client.secrets.kv.v2.create_or_update_secret(
            mount_point="secret",
            path="app/config",
            secret=secrets
        )
        
        print("Secrets stored in Vault at secret/app/config")
        print(f"Successfully injected {len(secrets)} secrets")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)