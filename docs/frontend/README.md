# Frontend Documentation

## Overview

The Nova frontend is built using React with TypeScript and Material-UI, providing a modern and responsive user interface for monitoring system health, managing alerts, and analyzing metrics.

## Testing

### Browser Support
- Primary: Safari (WebKit)
- Secondary: Chrome (optional)

### Running Tests
```bash
# Default (Safari)
npm run test:e2e
npm run test:e2e:update  # Update snapshots

# Chrome Testing
npm run test:e2e:chrome
npm run test:e2e:chrome:update  # Update snapshots
```

### Test Types
- Visual Regression Tests (`visual.spec.ts`)
- Component Tests (`*.test.ts`)
- Accessibility Tests (`accessibility.spec.ts`)

For detailed testing information, see [Testing Guide](../testing.md)

## Components

### Service Health (`ServiceHealth.tsx`)
- Real-time monitoring of system components
- Health Score display
- Component Status indicators
- Status filtering
- Search functionality
- Time range selection
- Responsive design
- Help tooltips

### Error Metrics (`ErrorMetrics.tsx`)
- Error tracking and visualization
- Category filtering
- Severity filtering
- Time-based analysis
- Export capabilities

### Alert Panel (`AlertPanel.tsx`)
- Recent alerts display
- Alert status management
- Priority filtering
- Responsive table layout

## Development

### Getting Started
```bash
# Install dependencies
npm install

# Start development server
npm start
```

### Code Style
- TypeScript for type safety
- Material-UI for components
- Responsive design patterns
- Accessibility first
- Component-based architecture

### Best Practices
1. Use TypeScript types
2. Follow Material-UI patterns
3. Implement responsive layouts
4. Add accessibility features
5. Include component tests
6. Update visual snapshots

For more details on specific components and features, see the respective documentation sections.
