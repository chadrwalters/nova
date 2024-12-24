"""Retry configuration for API calls."""

from pydantic import (
    BaseModel,
    Field,
    conint,
    confloat,
    model_validator
)

class RetryConfig(BaseModel):
    """Retry configuration for API calls."""
    max_attempts: conint(ge=1, le=10) = 3
    initial_delay: confloat(ge=0.1, le=5.0) = 1.0
    max_delay: confloat(ge=1.0, le=60.0) = 10.0
    exponential_base: confloat(ge=1.1, le=4.0) = 2.0
    jitter: bool = True
    jitter_factor: confloat(ge=0.0, le=0.5) = 0.1

    @model_validator(mode='after')
    def validate_delays(self) -> 'RetryConfig':
        """Validate delay values."""
        if self.initial_delay >= self.max_delay:
            raise ValueError("initial_delay must be less than max_delay")
        return self 