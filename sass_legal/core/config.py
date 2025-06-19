from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Application settings, loadable from environment variables or a .env file.

    Attributes:
        LOG_LEVEL: The logging level for the application (e.g., INFO, DEBUG, ERROR).
        API_PREFIX: The prefix for all API routes (e.g., /api/v1).
        APP_NAME: The name of the application.
        DEBUG: Boolean indicating if the application is in debug mode.
    """
    LOG_LEVEL: str = Field(default="INFO", description="Logging level for the application.")
    API_PREFIX: str = Field(default="/api/v1", description="URL prefix for all API routes.")
    APP_NAME: str = Field(default="Sass Legal", description="Name of the application.")
    DEBUG: bool = Field(default=False, description="Enable debug mode for the application.")

    class Config:
        """
        Pydantic settings configuration.
        Specifies the .env file to load settings from.
        """
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

if __name__ == "__main__":
    # For testing the settings loading
    print(f"App Name: {settings.APP_NAME}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"API Prefix: {settings.API_PREFIX}")
    print(f"Debug Mode: {settings.DEBUG}")
    # Example of how it would be overridden by an .env file:
    # Create a dummy .env file for this test:
    with open(".env", "w") as f:
        f.write("APP_NAME=My Awesome Sass Legal\n")
        f.write("DEBUG=True\n")

    print("\n--- After creating a .env file (will require re-running script to see effect on a new Settings() instance) ---")
    # settings_from_env = Settings() # This would show updated values if .env is read at instantiation
    # For this simple print, we'd need to re-instantiate or ensure .env is there before first Settings() call.
    # The current `settings` instance is already created.
    # To demonstrate, let's assume we re-instantiate (though in app, it's one instance)
    settings_after_env = Settings() # Pydantic-settings usually loads .env at instance creation.
    print(f"App Name (after .env): {settings_after_env.APP_NAME}")
    print(f"Debug Mode (after .env): {settings_after_env.DEBUG}")

    import os
    try:
        os.remove(".env") # Clean up dummy .env
    except FileNotFoundError:
        pass
