try:
    import openai
    print(f"OpenAI version: {openai.__version__}")
    from openai import OpenAI
    print("OpenAI import successful")
except Exception as e:
    print(f"OpenAI import failed: {e}")
except KeyboardInterrupt:
    print("OpenAI import interrupted")
