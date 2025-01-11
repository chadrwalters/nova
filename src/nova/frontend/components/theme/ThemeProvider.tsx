import { ReactNode } from 'react';
import { ThemeProvider as MuiThemeProvider, CssBaseline } from '@mui/material';
import { ThemeContext, useThemeProvider } from '../../hooks/useTheme';

interface ThemeProviderProps {
  children: ReactNode;
}

export default function ThemeProvider({ children }: ThemeProviderProps) {
  const themeContext = useThemeProvider();

  return (
    <ThemeContext.Provider value={themeContext}>
      <MuiThemeProvider theme={themeContext.theme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
} 