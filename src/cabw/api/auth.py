"""
API Authentication Layer

JWT-based authentication with PBAC for API access.
SecurityGovernor governs agent-to-agent AND API-to-simulation access.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto

import jwt
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext

from ...governance.security import Capability, SecurityContext, SecurityGovernor


class APIRole(Enum):
    """API access roles."""
    VIEWER = auto()      # Read-only access
    OPERATOR = auto()    # Can pause/resume, trigger events
    ADMIN = auto()       # Full control including agent injection
    SYSTEM = auto()      # Internal system access


@dataclass
class APIPrincipal:
    """Authenticated API principal."""
    principal_id: str
    role: APIRole
    capabilities: list[Capability] = field(default_factory=list)
    simulation_access: list[str] = field(default_factory=list)

    def has_capability(self, capability: Capability) -> bool:
        """Check if principal has capability."""
        return capability in self.capabilities

    def can_access_simulation(self, sim_id: str) -> bool:
        """Check if principal can access simulation."""
        return '*' in self.simulation_access or sim_id in self.simulation_access


# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


class APIAuthManager:
    """
    API Authentication and Authorization Manager.
    Uses same PBAC architecture as agent governance.
    """

    def __init__(self):
        self.governor = SecurityGovernor()
        self._users: dict[str, dict] = {}
        self._api_keys: dict[str, APIPrincipal] = {}

        # Setup default policies
        self._setup_policies()

    def _setup_policies(self):
        """Setup API access policies."""
        # Viewer policy
        from ...governance.security import SecurityPolicy

        viewer_policy = SecurityPolicy(
            policy_id='api_viewer',
            name='API Viewer Access',
            description='Read-only API access',
            rules=[
                lambda s, r, c, ctx: (
                    s.role in [APIRole.VIEWER, APIRole.OPERATOR, APIRole.ADMIN],
                    'Insufficient role'
                )
            ],
            required_capabilities=[Capability.READ]
        )
        self.governor.register_policy('api_viewer', viewer_policy)

        # Operator policy
        operator_policy = SecurityPolicy(
            policy_id='api_operator',
            name='API Operator Access',
            description='Can control simulations',
            rules=[
                lambda s, r, c, ctx: (
                    s.role in [APIRole.OPERATOR, APIRole.ADMIN],
                    'Insufficient role'
                )
            ],
            required_capabilities=[Capability.ACTION_EXECUTE]
        )
        self.governor.register_policy('api_operator', operator_policy)

        # Admin policy
        admin_policy = SecurityPolicy(
            policy_id='api_admin',
            name='API Admin Access',
            description='Full API access',
            rules=[
                lambda s, r, c, ctx: (
                    s.role == APIRole.ADMIN,
                    'Admin role required'
                )
            ],
            required_capabilities=[Capability.CREATE, Capability.DELETE, Capability.ADMIN]
        )
        self.governor.register_policy('api_admin', admin_policy)

    def create_user(
        self,
        username: str,
        password: str,
        role: APIRole,
        simulation_access: list[str] = None
    ) -> str:
        """Create a new API user."""
        hashed_password = pwd_context.hash(password)

        # Map role to capabilities
        role_capabilities = {
            APIRole.VIEWER: [Capability.READ],
            APIRole.OPERATOR: [Capability.READ, Capability.ACTION_EXECUTE],
            APIRole.ADMIN: [Capability.READ, Capability.ACTION_EXECUTE, Capability.CREATE, Capability.DELETE, Capability.ADMIN],
            APIRole.SYSTEM: [Capability.READ, Capability.ACTION_EXECUTE, Capability.CREATE, Capability.DELETE, Capability.ADMIN]
        }

        self._users[username] = {
            'username': username,
            'hashed_password': hashed_password,
            'role': role,
            'capabilities': role_capabilities.get(role, [Capability.READ]),
            'simulation_access': simulation_access or ['*'],
            'created_at': datetime.now().isoformat()
        }

        return username

    def authenticate_user(self, username: str, password: str) -> APIPrincipal | None:
        """Authenticate user and return principal."""
        user = self._users.get(username)
        if not user:
            return None

        if not pwd_context.verify(password, user['hashed_password']):
            return None

        return APIPrincipal(
            principal_id=username,
            role=user['role'],
            capabilities=user['capabilities'],
            simulation_access=user['simulation_access']
        )

    def create_access_token(
        self,
        principal: APIPrincipal,
        expires_delta: timedelta | None = None
    ) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            'sub': principal.principal_id,
            'role': principal.role.name,
            'capabilities': [c.name for c in principal.capabilities],
            'simulations': principal.simulation_access,
            'exp': expire
        }

        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str) -> APIPrincipal | None:
        """Verify JWT token and return principal."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            principal_id = payload.get('sub')
            role_name = payload.get('role')
            capabilities = payload.get('capabilities', [])
            simulations = payload.get('simulations', [])

            if not principal_id or not role_name:
                return None

            return APIPrincipal(
                principal_id=principal_id,
                role=APIRole[role_name],
                capabilities=[Capability[c] for c in capabilities if c in Capability.__members__],
                simulation_access=simulations
            )

        except JWTError:
            return None

    def check_api_access(
        self,
        principal: APIPrincipal,
        action: str,
        simulation_id: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Check if principal can perform API action.
        Uses same PBAC as agent governance.
        """
        # Check simulation access
        if simulation_id and not principal.can_access_simulation(simulation_id):
            return False, "Access denied to simulation"

        # Map action to policy
        policy_map = {
            'view': 'api_viewer',
            'list': 'api_viewer',
            'control': 'api_operator',  # start, pause, resume, stop
            'create': 'api_admin',      # create simulation, add agents
            'delete': 'api_admin',      # delete simulation
            'modify': 'api_operator'    # change weather, trigger events
        }

        policy_map.get(action, 'api_viewer')

        # Check through governor — pass plain dicts so evaluate_access can call .get()
        context = SecurityContext(
            subject_id=principal.principal_id,
            resource_id=simulation_id or 'api',
            action=action,
        )
        decision = self.governor.evaluate_access(
            subject={'id': principal.principal_id, 'type': 'api_principal'},
            resource={'id': simulation_id or 'api', 'type': action},
            capability=Capability.ACTION_EXECUTE,
            context=context.to_dict(),
        )
        return decision.granted, decision.reason


# Global auth manager
auth_manager = APIAuthManager()


# FastAPI dependency
async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIPrincipal:
    """FastAPI dependency to get current authenticated principal."""
    token = credentials.credentials
    principal = auth_manager.verify_token(token)

    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return principal


async def require_capability(capability: Capability):
    """Create dependency requiring specific capability."""
    async def checker(principal: APIPrincipal = Depends(get_current_principal)):
        if not principal.has_capability(capability):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required capability: {capability.name}"
            )
        return principal
    return checker


async def require_simulation_access(sim_id: str):
    """Create dependency requiring simulation access."""
    async def checker(principal: APIPrincipal = Depends(get_current_principal)):
        if not principal.can_access_simulation(sim_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to simulation"
            )
        return principal
    return checker


class WebSocketAuth:
    """WebSocket authentication handler."""

    @staticmethod
    async def authenticate(websocket: WebSocket) -> APIPrincipal | None:
        """Authenticate WebSocket connection."""
        # Get token from query params or headers
        token = websocket.query_params.get('token')

        if not token:
            # Try headers
            auth_header = websocket.headers.get('authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]

        if not token:
            await websocket.close(code=4001, reason="Missing authentication")
            return None

        principal = auth_manager.verify_token(token)

        if not principal:
            await websocket.close(code=4002, reason="Invalid authentication")
            return None

        return principal


# Default users (for development)
def create_default_users():
    """Create default users for development."""
    auth_manager.create_user(
        username='viewer',
        password='viewer123',
        role=APIRole.VIEWER
    )

    auth_manager.create_user(
        username='operator',
        password='operator123',
        role=APIRole.OPERATOR
    )

    auth_manager.create_user(
        username='admin',
        password='admin123',
        role=APIRole.ADMIN
    )


# Initialize
create_default_users()
