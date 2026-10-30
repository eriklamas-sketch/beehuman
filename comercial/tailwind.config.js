// Configuración de Tailwind de la página comercial (propuesta visual de Gemini aprobada).
// Solo procesa el index.html de la raíz: la app (app/) no usa estos estilos.
module.exports = {
  content: ['../index.html'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        amber: { 500: '#f59e0b', 600: '#d97706', 700: '#b45309' },
        navy: { 900: '#0f172a', 950: '#090d16' }
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] }
    }
  }
};
