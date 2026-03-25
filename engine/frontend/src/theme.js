import { createTheme } from '@mui/material/styles';
import config from './agentConfig.json';

const { primary_color, secondary_color, fonts } = config.branding;
const bgColor = config.branding.background || '#FBF9F7';

const theme = createTheme({
  palette: {
    primary: {
      main: primary_color,
      light: primary_color + 'CC',
      dark: primary_color,
    },
    secondary: {
      main: secondary_color,
    },
    background: {
      default: bgColor,
      paper: '#FFFFFF',
    },
  },
  typography: {
    fontFamily: `"${fonts.body}", -apple-system, BlinkMacSystemFont, sans-serif`,
    h1: { fontFamily: `"${fonts.heading}", cursive` },
    h2: { fontFamily: `"${fonts.heading}", cursive` },
    h3: { fontFamily: `"${fonts.heading}", cursive` },
    h4: { fontFamily: `"${fonts.heading}", cursive` },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
});

export default theme;
