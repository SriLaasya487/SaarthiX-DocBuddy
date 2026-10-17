from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./docbuddy.db"
    jwt_secret: str = "dev-secret-change-me"
    data_key: str = "dev-data-key-change-me"       # derives the Fernet key that encrypts sensitive text columns
    debug: bool = True
    cors_origins: str = "http://localhost:5173"
    fall_response_seconds: int = 60
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_rate_per_hour: int = 6
    media_dir: str = "./media"
    admin_phones: str = ""                          # comma separated; only these may sign up as moderator
    public_url: str = "http://localhost:5173"

    # channels (all optional - without them messages are only written to the outbox + log)
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_template: str = "docbuddy_alert"
    sms_url: str = ""                               # generic HTTP SMS gateway (MSG91 / Twilio / Exotel style)
    sms_key: str = ""
    sms_sender: str = "DOCBDY"
    ivr_provider_url: str = ""                      # outbound call API (Exotel / Twilio / Knowlarity)
    ivr_provider_key: str = ""
    fcm_key: str = ""

    # AI companion (optional). Without a key a rule-based companion is used.
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-4-5"

    # business
    enforce_tiers: bool = False                     # when False every feature is open (dev/demo)
    price_family_inr: int = 149                     # placeholders - set your own pricing
    price_care_inr: int = 399

    model_config = {"env_file": ".env"}


settings = Settings()
