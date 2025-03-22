from dataclasses import dataclass
from typing import Optional

@dataclass
class TxOpts:
    """Transaction options."""
    
    skip_preflight: bool = False
    """If true, skip the preflight transaction checks."""
    
    preflight_commitment: Optional[str] = None
    """Commitment level to use for preflight."""
    
    skip_confirmation: bool = False
    """If true, don't wait for transaction confirmation."""
    
    commitment: Optional[str] = None
    """Commitment level."""
    
    def __init__(
        self,
        skip_preflight: bool = False,
        preflight_commitment: Optional[str] = None,
        skip_confirmation: bool = False,
        commitment: Optional[str] = None,
    ):
        """Init transaction options."""
        self.skip_preflight = skip_preflight
        self.preflight_commitment = preflight_commitment
        self.skip_confirmation = skip_confirmation
        self.commitment = commitment 