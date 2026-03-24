const fs = require('fs');
const path = require('path');

// Step 1: Dynamic mappings based on available icons
const iconsDir = path.join(__dirname, '../../icons');
const iconFiles = fs.readdirSync(iconsDir).filter(file => file.endsWith('.png'));

const dynamicMappings = {};
iconFiles.forEach(file => {
  const tag = `[${file.split('.')[0].toUpperCase()}]`; // Example: action.png -> [ACTION]
  dynamicMappings[tag] = `/static/icons/${file}`;
});

// Step 2: Render habilidad function
function renderHabilidad(habilidad) {
  let processedHabilidad = habilidad;

  Object.entries(dynamicMappings).forEach(([tag, iconPath]) => {
    const regex = new RegExp(tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
    processedHabilidad = processedHabilidad.replace(regex, `<img src='${iconPath}' class='inline-icon' />`);
  });

  return processedHabilidad;
}

module.exports = { renderHabilidad };