"""Base Pydantic model configuration for ASAP protocol models.

All ASAP models inherit from ASAPBaseModel to ensure consistent behavior:
- Immutability (frozen=True) for thread-safety and predictability
- Strict validation (extra="forbid") to catch typos and invalid fields
- Flexible field naming (populate_by_name=True) for alias support
- JSON Schema generation with proper metadata
"""

from pydantic import BaseModel, ConfigDict


class ASAPBaseModel(BaseModel):
    """Base model for all ASAP protocol entities.
    
    This base class provides:
    - **Immutability**: Models are frozen after creation (thread-safe)
    - **Strict validation**: Extra fields are forbidden (catches errors early)
    - **Flexible naming**: Fields can be populated by name or alias
    - **JSON Schema**: Proper schema generation for interoperability
    
    Example:
        >>> from pydantic import Field
        >>> class MyModel(ASAPBaseModel):
        ...     name: str
        ...     count: int = Field(default=0, ge=0)
        >>> 
        >>> obj = MyModel(name="test", count=5)
        >>> obj.name
        'test'
        >>> obj.count = 10  # Raises ValidationError (frozen)
        Traceback (most recent call last):
        ...
        pydantic_core._pydantic_core.ValidationError: ...
    """
    
    model_config = ConfigDict(
        # Immutability: prevents accidental mutations after creation
        frozen=True,
        
        # Strict validation: reject unknown fields to catch typos
        extra="forbid",
        
        # Allow populating fields by both name and alias
        populate_by_name=True,
        
        # JSON Schema configuration
        # Use enum values (not names) in schema
        use_enum_values=False,
        
        # Validate default values
        validate_default=True,
        
        # Validate assignments (only relevant if frozen=False)
        validate_assignment=True,
        
        # JSON Schema extras for better documentation
        json_schema_extra={
            "additionalProperties": False,
        },
    )
