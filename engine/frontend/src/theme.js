import { createTheme } from '@mui/material/styles';
import config from './agentConfig.json';

const { primary_color, secondary_color, fonts } = config.branding;
const bgColor = config.branding.background || '#FBF9F7';

const baseTypography = {
  fontFamily: `"${fonts.body}", -apple-system, BlinkMacSystemFont, sans-serif`,
  h1: { fontFamily: `"${fonts.heading}", cursive` },
  h2: { fontFamily: `"${fonts.heading}", cursive` },
  h3: { fontFamily: `"${fonts.heading}", cursive` },
  h4: { fontFamily: `"${fonts.heading}", cursive` },
};

const baseComponents = {
  MuiButton: {
    styleOverrides: {
      root: { textTransform: 'none', fontWeight: 600 },
    },
  },
};

export const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: primary_color, light: primary_color + 'CC', dark: primary_color },
    secondary: { main: secondary_color },
    background: { default: bgColor, paper: '#FFFFFF' },
  },
  typography: baseTypography,
  shape: { borderRadius: 8 },
  components: baseComponents,
});

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: secondary_color, light: secondary_color + 'CC', dark: secondary_color },
    secondary: { main: secondary_color },
    background: { default: '#1A1A1A', paper: '#2A2A2A' },
    text: { primary: '#E8E8E8', secondary: '#A0A0A0' },
  },
  typography: baseTypography,
  shape: { borderRadius: 8 },
  components: baseComponents,
});

// Default export for backwards compatibility
export default lightTheme;
