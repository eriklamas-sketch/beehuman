# Página comercial · estilos y recursos

La página comercial es `index.html` en la raíz del repositorio (base visual: propuesta de Gemini aprobada).
Vercel la sirve tal cual: **no hay paso de compilación en el despliegue**. Esta carpeta solo contiene
las herramientas para regenerar los recursos ya compilados que viven en `assets/`.

| Recurso | Origen | Licencia |
|---|---|---|
| `assets/comercial.css` | Tailwind CSS 3.4.17 compilado desde `estilos.css` + `tailwind.config.js` | MIT |
| `assets/fonts/inter-*.woff2` | Inter (@fontsource/inter 5.1.1) | SIL OFL 1.1 (`assets/fonts/Inter-OFL.txt`) |
| Iconos SVG dentro de `index.html` | Font Awesome Free 6.7.2 | Iconos CC BY 4.0 |
| Logo | Símbolo del Logo 1 aprobado de BeeHuman (el mismo de la app) | Propio |

## Después de editar `index.html`

```bash
cd comercial
npm install        # solo la primera vez
npm run css        # vuelve a generar assets/comercial.css con las clases usadas
```

Se debe hacer commit de `assets/comercial.css` regenerado junto con el cambio de `index.html`;
si se agrega una clase de Tailwind nueva y no se recompila, esa clase no tendrá estilo.

Para un icono nuevo: copiar el SVG de `node_modules/@fortawesome/fontawesome-free/svgs/`
con la clase `bh-i` y `fill="currentColor"`, como los demás iconos de la página.
