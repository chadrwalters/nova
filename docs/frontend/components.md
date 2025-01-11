# Frontend Components

## Core Components

### App Component
The main application component that provides the layout structure and theme context.

- **Features**:
  - Responsive layout using Material-UI
  - Main landmark for accessibility
  - Proper heading hierarchy with h1
  - Settings button with proper ARIA labels
  - Grid-based component layout

### ServiceHealth Component
Displays the health status of various services with filtering capabilities.

- **Features**:
  - Status filter dropdown (All, Healthy, Warning, Error)
  - Uptime display
  - Keyboard accessible controls
  - Proper ARIA labels and roles
  - Data testid attributes for testing

### ErrorMetrics Component
Shows error metrics with severity-based filtering.

- **Features**:
  - Severity filter dropdown (All, Low, Medium, High, Critical)
  - Error rate display
  - Keyboard accessible controls
  - Proper ARIA labels and roles
  - Data testid attributes for testing

### AlertPanel Component
Displays recent alerts in a table format.

- **Features**:
  - Sortable columns
  - Time, Severity, Message, and Status display
  - Accessible table structure
  - Proper ARIA labels
  - Data testid attributes for testing

## Accessibility Features

- Proper landmark structure (main, banner)
- Semantic heading hierarchy
- ARIA labels for interactive elements
- Keyboard navigation support
- Focus management
- Screen reader friendly content
- High contrast text

## Testing

Components include:
- Data testid attributes for e2e testing
- Accessibility testing setup
- Visual regression tests
- Unit tests for component logic
- Integration tests for component interaction

## Theme Support

- Light/Dark mode support
- Consistent spacing using MUI system
- Responsive design breakpoints
- Typography scale
- Color palette
