import os
from openai import OpenAI
from nova.utils.console import console

def setup_openai_client() -> OpenAI:
    """Set up OpenAI client.
    
    Returns:
        OpenAI client instance
    
    Raises:
        ValueError: If OpenAI API key not found or invalid
    """
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        console.print("[warning]OpenAI API key not found. Image descriptions will be limited.[/]")
        raise ValueError("OpenAI API key not found")
        
    if api_key.startswith('sk-proj-'):
        console.print("[warning]Project-scoped API key detected. Some features may be limited.[/]")
    
    # Initialize client
    client = OpenAI(api_key=api_key)
    
    # Test connection with vision model
    try:
        # First test basic chat completion
        response = client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[{"role": "user", "content": "Test connection"}],
            max_tokens=1
        )
        
        console.print("OpenAI chat model initialized successfully")
        return client
        
    except Exception as e:
        console.print(f"[warning]Failed to initialize OpenAI client: {e}[/]")
        raise ValueError(f"OpenAI API error: {str(e)}")