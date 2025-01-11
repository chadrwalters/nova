# Nova Dashboard

A modern monitoring dashboard built with React and Material-UI, focusing on accessibility and user experience.

## Features

- Real-time service health monitoring
- Error metrics tracking with severity filtering
- Alert management system
- Responsive design
- Accessibility compliant
- Dark/Light theme support

## Getting Started

### Prerequisites

- Node.js 16+
- npm or yarn
- Poetry for Python dependencies

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nova.git
   cd nova
   ```

2. Install dependencies:
   ```bash
   poetry install
   cd src/nova/frontend
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

## Testing

Run the test suite:
```bash
npm test
```

Run visual regression tests:
```bash
npm run test:visual
```

Run accessibility tests:
```bash
npm run test:a11y
```

## Project Structure

```
src/nova/
├── frontend/           # Frontend application
│   ├── src/
│   │   ├── components/ # React components
│   │   ├── theme/      # Theme configuration
│   │   └── App.tsx     # Main application
│   ├── tests/          # Test suites
│   └── package.json    # Frontend dependencies
└── backend/           # Backend services
```

## Development Status

- ✅ Core components implemented
- ✅ Basic UI functionality
- ✅ Accessibility features
- 🚧 Test coverage (in progress)
- 📝 Documentation
- 🔄 Continuous Integration

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
