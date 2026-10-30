// Copia Inter (OFL 1.1) a ../assets/fonts para alojarla junto a la página.
const fs = require('fs'), path = require('path');
const origen = path.join(__dirname, 'node_modules/@fontsource/inter');
const destino = path.join(__dirname, '../assets/fonts');
fs.mkdirSync(destino, { recursive: true });
for (const w of [300, 400, 500, 600, 700, 800]) {
  const f = `inter-latin-${w}-normal.woff2`;
  fs.copyFileSync(path.join(origen, 'files', f), path.join(destino, f));
}
fs.copyFileSync(path.join(origen, 'LICENSE'), path.join(destino, 'Inter-OFL.txt'));
console.log('Fuentes copiadas en assets/fonts');
