def setup_openai_client() -> Optional[OpenAI]:
    """Set up OpenAI client with API key from environment.
    
    Returns:
        OpenAI client instance if successful, None otherwise
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning("OpenAI API key not found. Image descriptions will be limited.")
        return None
        
    try:
        client = OpenAI(api_key=api_key)
        # Test connection with a simple completion
        response = client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[{"role": "user", "content": "Test connection"}],
            max_tokens=5
        )
        logger.info("OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        return None 