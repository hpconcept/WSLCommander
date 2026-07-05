# WSL Commander - Container Support Design

## Overview
This document outlines the design for adding WSL container support to WSL Commander.

## Architecture Decision: Unified Page with Filters

### Design Choice
- **Single "Distributions" page** showing both WSL distros AND containers
- **Filter mechanism** to toggle visibility: All | Distros Only | Containers Only
- **Expandable cards** for containers to show detailed information without cluttering

### UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Installed Distributions                          🔄         │
├─────────────────────────────────────────────────────────────┤
│  Filter: [All ▼] [Distros Only] [Containers Only]           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [🐧] Ubuntu-22.04          ● Running  WSL2          │   │  <- Distro Card
│  │      [Set Default] [Export]  [Stop] [Remove]        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [🐳] nginx-web            ● Running                  │   │  <- Container Card (collapsed)
│  │      Ports: 80:8080/tcp   Image: nginx:latest        │   │
│  │      [▼ Details] [Stop] [Remove] [Logs]             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [🐳] postgres-db          ● Running                  │   │  <- Container Card (expanded)
│  │      Ports: 5432:5432/tcp   Image: postgres:14       │   │
│  │      [▲ Details] [Stop] [Remove] [Logs]             │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ ID: abc123def456                               │  │   │
│  │  │ Volumes:                                       │  │   │
│  │  │   • /data/postgres:/var/lib/postgresql/data    │  │   │
│  │  │ Environment:                                   │  │   │
│  │  │   • POSTGRES_PASSWORD=***                      │  │   │
│  │  │   • POSTGRES_DB=myapp                          │  │   │
│  │  │ Resources:                                     │  │   │
│  │  │   • CPU: 2.5%  Memory: 128MB / 512MB          │  │   │
│  │  │ Network: bridge  Restart: unless-stopped       │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Structure

### Models
- `Distro` (existing) - WSL distribution model
- `Container` (new) - WSL container model with ports, volumes, etc.
- `EntityType` (new) - Enum to distinguish entity types
- `PortMapping`, `VolumeMapping` - Container-specific data structures

### Cards
- `DistroCard` (existing) - Card for WSL distributions
- `ContainerCard` (new) - Expandable card for containers
  - Collapsed: Name, image, status, port summary, basic actions
  - Expanded: Full details including volumes, env vars, resources

### Workers
- `wsl_worker.py` (existing) - WSL distribution operations
- `container_worker.py` (new) - Container operations:
  - `ListContainersWorker` - List all containers
  - `CreateContainerWorker` - Create a new container
  - `StartContainerWorker` - Start a container
  - `StopContainerWorker` - Stop a container
  - `RemoveContainerWorker` - Remove a container
  - `GetContainerLogsWorker` - Fetch container logs
  - `InspectContainerWorker` - Get detailed container info

### Pages
- `distros_page.py` - Modified to show both distros and containers
  - Add filter buttons/dropdown
  - Handle mixed card types
  - Unified refresh mechanism
- `container_create_page.py` (new) - Create containers
  - Manual container creation form
  - Docker Compose import functionality

## Filter Implementation

### Filter States
```python
class EntityFilter(Enum):
    ALL = "all"
    DISTROS_ONLY = "distros"
    CONTAINERS_ONLY = "containers"
```

### Filter Logic
- Cards are shown/hidden based on filter state
- Filter persists during session (saved in page state)
- Default: Show all

## Card Expansion Behavior

### Interaction
- Click "▼ Details" button to expand
- Click "▲ Details" button to collapse
- Only one container card expanded at a time (auto-collapse others)
- Smooth animation for expand/collapse

### Expanded Content
- Container ID (short)
- All port mappings
- All volume mounts
- Environment variables (passwords masked)
- Resource usage (CPU, Memory)
- Network mode
- Restart policy
- Created timestamp

## Visual Differentiation

### Logo Strategy
- Distros: Use distribution-specific logos (ubuntu.png, debian.png, etc.)
- Containers: 
  - Primary: docker.png
  - Future: Detect base image and use corresponding logo
    - nginx-based → custom nginx icon or docker.png
    - ubuntu-based → ubuntu.png with small docker badge
  
### Badge Indicators
- Distros: "★ Default" badge for default distro
- Containers: Different colored status indicator
  - Running: Green (●)
  - Stopped: Gray (●)
  - Paused: Yellow (●)

### Card Styling
- Distros: Current styling (subtle gradient or solid)
- Containers: Slightly different border or accent color to distinguish at a glance

## Technical Considerations

### Performance
- Listing containers may be slower than listing distros
- Use separate workers for each entity type
- Run in parallel, merge results
- Cache expanded state to avoid re-fetching

### Error Handling
- If container API not available (old WSL version), hide container filter option
- Show info message: "Container support requires WSL version X.X or higher"
- Gracefully degrade to distros-only mode

### State Management
- Track which containers are expanded
- Store filter preference
- Handle refresh while maintaining expanded state

## Future Enhancements (Post-MVP)

1. **Search/Filter by name** - Text filter in addition to type filter
2. **Sorting** - Sort by name, status, resource usage
3. **Bulk operations** - Select multiple items, stop/start all
4. **Resource graphs** - Small CPU/memory sparklines on cards
5. **Quick actions menu** - Right-click context menu
6. **Container stats dashboard** - Overview of total resource usage
7. **Network visualization** - Show containers on same network

## Implementation Phases

### Phase 1: Foundation (When WSL containers release)
- Create Container model
- Create ContainerWorker with basic operations
- Update DistrosPage to support mixed entities
- Implement filter UI
- Basic ContainerCard (no expansion yet)

### Phase 2: Enhanced Cards
- Implement expandable ContainerCard
- Add detailed information display
- Add container logs viewing
- Improve visual differentiation

### Phase 3: Container Creation
- Create container_create_page.py
- Build manual creation form
- Implement basic container creation

### Phase 4: Docker Compose Support
- Add compose file parser
- Import compose files
- Auto-populate creation form from compose

## Notes

- Wait for official Microsoft WSL container release before implementing
- Monitor Microsoft documentation for exact CLI commands


