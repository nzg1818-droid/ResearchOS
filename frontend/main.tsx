import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import App from "./App";
import "./style.css";
const theme = createTheme({
  palette: {
    primary: { main: "#1c665f" },
    secondary: { main: "#bd7543" },
    background: { default: "#f5f7fa" },
  },
  typography: { fontFamily: '"Segoe UI", sans-serif', h4: { fontWeight: 650 } },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: { styleOverrides: { root: { textTransform: "none" } } },
  },
});
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>,
);
