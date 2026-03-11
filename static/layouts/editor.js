(function () {
    const stage = document.getElementById('layout-stage');
    if (!stage) {
        return;
    }

    const overlays = document.getElementById('layout-overlays');
    const cardTypeSelect = document.getElementById('layout-card-type');
    const layoutSelect = document.getElementById('layout-select');
    const statusEl = document.getElementById('layout-status');
    const selectedNameEl = document.getElementById('layout-selected-name');
    const csrfToken = (document.getElementById('csrf-token') || {}).value || '';
    const propX = document.getElementById('prop-x');
    const propY = document.getElementById('prop-y');
    const propWidth = document.getElementById('prop-width');
    const propHeight = document.getElementById('prop-height');
    const propAlign = document.getElementById('prop-align');
    const propAnchorMode = document.getElementById('prop-anchor-mode');
    const propMinFontSize = document.getElementById('prop-min-font-size');
    const propAutoshrinkEnabled = document.getElementById('prop-autoshrink-enabled');
    const propEllipsisEnabled = document.getElementById('prop-ellipsis-enabled');
    const propShadowEnabled = document.getElementById('prop-shadow-enabled');
    const applyButton = document.getElementById('apply-properties');

    const initialLayouts = JSON.parse((document.getElementById('layout-initial-layouts') || { textContent: '[]' }).textContent || '[]');
    const initialMeta = JSON.parse((document.getElementById('layout-initial-meta') || { textContent: '{}' }).textContent || '{}');

    const state = {
        cardType: initialMeta.card_type || 'cripta',
        layouts: initialLayouts,
        activeLayoutId: initialMeta.active_layout_id,
        selectedLayer: null,
        config: null,
    };

    const layerOrder = ['nombre', 'clan', 'senda', 'disciplinas', 'simbolos', 'habilidad', 'coste', 'cripta', 'ilustrador'];
    const textRuleLayers = ['nombre', 'ilustrador'];

    function setStatus(message, type) {
        statusEl.textContent = message || '';
        statusEl.style.color = type === 'error' ? '#b42318' : '#05603a';
    }

    function debounce(fn, delay) {
        let timeoutId = null;
        return function () {
            const args = arguments;
            clearTimeout(timeoutId);
            timeoutId = setTimeout(function () {
                fn.apply(null, args);
            }, delay);
        };
    }

    function getActiveLayout() {
        if (state.activeLayoutId == null) {
            return null;
        }
        return state.layouts.find(function (layout) {
            return layout.id === state.activeLayoutId;
        }) || null;
    }

    function clone(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function refreshLayoutSelect() {
        layoutSelect.innerHTML = '';
        state.layouts.forEach(function (layout) {
            const option = document.createElement('option');
            option.value = String(layout.id);
            option.textContent = layout.is_default ? layout.name + ' (default)' : layout.name;
            if (layout.id === state.activeLayoutId) {
                option.selected = true;
            }
            layoutSelect.appendChild(option);
        });

        if (state.layouts.length === 0) {
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = 'No hay layouts';
            layoutSelect.appendChild(emptyOption);
            state.activeLayoutId = null;
        }
    }

    function sectionForLayer(layerName) {
        return state.config ? state.config[layerName] : null;
    }

    function ensureSectionRules(layerName, section) {
        if (!section.rules || typeof section.rules !== 'object') {
            section.rules = {};
        }
        if (section.rules.align == null) {
            section.rules.align = layerName === 'nombre' ? 'center' : 'left';
        }
        if (section.rules.anchor_mode == null) {
            section.rules.anchor_mode = 'free';
        }
        if (section.rules.min_font_size == null) {
            section.rules.min_font_size = layerName === 'ilustrador' ? 14 : 18;
        }
        if (section.rules.autoshrink == null) {
            section.rules.autoshrink = true;
        }
        if (section.rules.ellipsis_enabled == null) {
            section.rules.ellipsis_enabled = true;
        }
    }

    function ensureSectionShadow(section) {
        if (!section.shadow || typeof section.shadow !== 'object') {
            section.shadow = {};
        }
        if (section.shadow.enabled == null) {
            section.shadow.enabled = false;
        }
    }

    function updateAdvancedInputs(layerName, section) {
        const isTextLayer = textRuleLayers.includes(layerName);
        const advancedInputs = [
            propAlign,
            propAnchorMode,
            propMinFontSize,
            propAutoshrinkEnabled,
            propEllipsisEnabled,
            propShadowEnabled,
        ];
        advancedInputs.forEach(function (input) {
            input.disabled = !isTextLayer;
        });

        if (!isTextLayer || !section) {
            propAlign.value = 'left';
            propAnchorMode.value = 'free';
            propMinFontSize.value = '';
            propAutoshrinkEnabled.checked = false;
            propEllipsisEnabled.checked = false;
            propShadowEnabled.checked = false;
            return;
        }

        ensureSectionRules(layerName, section);
        ensureSectionShadow(section);
        propAlign.value = section.rules.align;
        propAnchorMode.value = section.rules.anchor_mode;
        propMinFontSize.value = Number(section.rules.min_font_size || 0);
        propAutoshrinkEnabled.checked = Boolean(section.rules.autoshrink);
        propEllipsisEnabled.checked = Boolean(section.rules.ellipsis_enabled);
        propShadowEnabled.checked = Boolean(section.shadow.enabled);
    }

    function frameFromSection(layerName, section, carta) {
        const cardWidth = Number(carta.width || 745);
        const cardHeight = Number(carta.height || 1040);
        if (section.box && typeof section.box === 'object') {
            return {
                x: Math.max(0, Math.round(Number(section.box.x || 0))),
                y: Math.max(0, Math.round(Number(section.box.y || 0))),
                width: Math.max(30, Math.round(Number(section.box.width || 30))),
                height: Math.max(30, Math.round(Number(section.box.height || 30))),
            };
        }

        let x = Number(section.x || 0);
        let y = Number(section.y || 0);
        if (layerName === 'nombre' && typeof section.y === 'number' && section.y < 2) {
            y = Math.round(cardHeight * section.y);
        }
        if (layerName === 'habilidad' && section.y_ratio != null) {
            y = Math.round(cardHeight * Number(section.y_ratio || 0));
        }

        let width = Number(section.size || section.font_size || 120);
        let height = Number(section.size || section.font_size || 120);

        if (layerName === 'habilidad') {
            width = Math.round(cardWidth * Number(section.max_width_ratio || 0.5));
            if (section.box_bottom_ratio != null) {
                height = Math.max(40, Math.round(cardHeight * Number(section.box_bottom_ratio || 0.8)) - y);
            } else {
                height = 170;
            }
        } else if (layerName === 'coste') {
            if (section.left != null) {
                width = 120;
            }
            x = Number(section.left != null ? section.left : cardWidth - Number(section.right || 40) - width);
            y = cardHeight - Number(section.bottom || 45) - height;
        } else if (layerName === 'disciplinas' || layerName === 'simbolos') {
            height = Math.max(60, Number(section.spacing || 80) * 3);
        } else if (layerName === 'cripta') {
            width = 90;
            height = 60;
            const hab = state.config.habilidad || {};
            const habY = hab.y_ratio != null ? Math.round(cardHeight * Number(hab.y_ratio || 0.8)) : 820;
            y = habY - Number(section.font_size || 35) - Number(section.y_gap || 1);
        } else if (layerName === 'ilustrador') {
            width = 210;
            y = cardHeight - Number(section.bottom || 20) - height;
        }

        return {
            x: Math.max(0, Math.round(x)),
            y: Math.max(0, Math.round(y)),
            width: Math.max(30, Math.round(width)),
            height: Math.max(30, Math.round(height)),
        };
    }

    function applyFrameToSection(layerName, section, frame, carta) {
        const cardWidth = Number(carta.width || 745);
        const cardHeight = Number(carta.height || 1040);
        section.x = Math.round(frame.x);
        section.y = Math.round(frame.y);
        section.box = {
            x: Math.round(frame.x),
            y: Math.round(frame.y),
            width: Math.max(30, Math.round(frame.width)),
            height: Math.max(30, Math.round(frame.height)),
        };

        if (layerName === 'nombre') {
            section.font_size = Math.max(8, Math.round(frame.height));
        } else if (layerName === 'clan' || layerName === 'senda') {
            section.size = Math.max(8, Math.round(Math.max(frame.width, frame.height)));
        } else if (layerName === 'disciplinas' || layerName === 'simbolos') {
            section.size = Math.max(8, Math.round(frame.width));
            section.spacing = Math.max(0, Math.round(frame.height / 3));
        } else if (layerName === 'habilidad') {
            section.max_width_ratio = Math.max(0, Math.min(1, frame.width / cardWidth));
            section.y_ratio = Math.max(0, Math.min(1, frame.y / cardHeight));
            section.box_bottom_ratio = Math.max(0, Math.min(1, (frame.y + frame.height) / cardHeight));
            section.font_size = Math.max(8, Math.round(frame.height / 4));
        } else if (layerName === 'coste') {
            section.bottom = Math.max(0, Math.round(cardHeight - frame.y - frame.height));
            section.right = Math.max(0, Math.round(cardWidth - frame.x - frame.width));
            section.size = Math.max(8, Math.round(frame.height));
        } else if (layerName === 'cripta') {
            section.font_size = Math.max(8, Math.round(frame.height));
            const hab = state.config.habilidad || {};
            const habY = hab.y_ratio != null ? Math.round(cardHeight * Number(hab.y_ratio || 0.8)) : 820;
            section.y_gap = Math.max(0, Math.round(habY - frame.y - section.font_size));
        } else if (layerName === 'ilustrador') {
            section.bottom = Math.max(0, Math.round(cardHeight - frame.y - frame.height));
            section.font_size = Math.max(8, Math.round(frame.height));
        }
    }

    function updatePropertyInputs(frame) {
        propX.value = frame ? frame.x : '';
        propY.value = frame ? frame.y : '';
        propWidth.value = frame ? frame.width : '';
        propHeight.value = frame ? frame.height : '';
    }

    function setActiveLayer(layerName) {
        state.selectedLayer = layerName;
        Array.from(overlays.querySelectorAll('.layout-layer')).forEach(function (layer) {
            layer.classList.toggle('active', layer.dataset.layer === layerName);
        });

        if (!layerName) {
            selectedNameEl.textContent = 'Selecciona una capa';
            updatePropertyInputs(null);
            updateAdvancedInputs(null, null);
            return;
        }

        selectedNameEl.textContent = layerName;
        const section = sectionForLayer(layerName);
        if (!section) {
            updatePropertyInputs(null);
            updateAdvancedInputs(null, null);
            return;
        }
        const frame = frameFromSection(layerName, section, state.config.carta || {});
        updatePropertyInputs(frame);
        updateAdvancedInputs(layerName, section);
    }

    function applyAdvancedProperties(layerName, section) {
        if (!layerName || !section) {
            return;
        }

        if (!section.rules || typeof section.rules !== 'object') {
            section.rules = {};
        }
        section.rules.anchor_mode = propAnchorMode.value || 'free';

        if (!textRuleLayers.includes(layerName)) {
            return;
        }

        ensureSectionRules(layerName, section);
        ensureSectionShadow(section);
        section.rules.align = propAlign.value || section.rules.align;
        section.rules.min_font_size = Math.max(8, Number(propMinFontSize.value || section.rules.min_font_size || 12));
        section.rules.autoshrink = Boolean(propAutoshrinkEnabled.checked);
        section.rules.ellipsis_enabled = Boolean(propEllipsisEnabled.checked);
        section.shadow.enabled = Boolean(propShadowEnabled.checked);
    }

    function getFrameFromElement(el) {
        return {
            x: Number(el.style.left.replace('px', '')) || 0,
            y: Number(el.style.top.replace('px', '')) || 0,
            width: Number(el.style.width.replace('px', '')) || 30,
            height: Number(el.style.height.replace('px', '')) || 30,
        };
    }

    function renderLayers() {
        overlays.innerHTML = '';
        const activeLayout = getActiveLayout();
        if (!activeLayout) {
            state.config = null;
            setStatus('Crea un layout para empezar.', 'error');
            setActiveLayer(null);
            return;
        }

        state.config = clone(activeLayout.config || {});
        const carta = state.config.carta || { width: 745, height: 1040 };
        stage.style.aspectRatio = Number(carta.width || 745) + ' / ' + Number(carta.height || 1040);

        layerOrder.forEach(function (layerName) {
            const section = sectionForLayer(layerName);
            if (!section || typeof section !== 'object') {
                return;
            }

            const frame = frameFromSection(layerName, section, carta);
            const layer = document.createElement('div');
            layer.className = 'layout-layer';
            layer.dataset.layer = layerName;
            layer.style.left = frame.x + 'px';
            layer.style.top = frame.y + 'px';
            layer.style.width = frame.width + 'px';
            layer.style.height = frame.height + 'px';

            const label = document.createElement('span');
            label.className = 'layout-layer-label';
            label.textContent = layerName;
            layer.appendChild(label);

            layer.addEventListener('click', function () {
                setActiveLayer(layerName);
            });

            overlays.appendChild(layer);
        });

        if (state.selectedLayer) {
            setActiveLayer(state.selectedLayer);
        }
    }

    async function fetchLayoutsByCardType(cardType) {
        const response = await fetch('/layouts/api/list?card_type=' + encodeURIComponent(cardType));
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || 'No se pudo cargar layouts');
        }

        state.layouts = payload.layouts || [];
        const defaultLayout = state.layouts.find(function (layout) { return layout.is_default; });
        state.activeLayoutId = defaultLayout ? defaultLayout.id : (state.layouts[0] ? state.layouts[0].id : null);
        refreshLayoutSelect();
        renderLayers();
    }

    async function saveConfig() {
        if (!state.activeLayoutId || !state.config) {
            setStatus('No hay layout activo para guardar.', 'error');
            return;
        }

        const response = await fetch('/layouts/api/update-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                layout_id: state.activeLayoutId,
                config: state.config,
            }),
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || 'No se pudo guardar');
        }

        const index = state.layouts.findIndex(function (layout) {
            return layout.id === state.activeLayoutId;
        });
        if (index >= 0) {
            state.layouts[index] = payload.layout;
        }
        setStatus('Config guardada');
    }

    async function requestPreview() {
        if (!state.config || !state.activeLayoutId) {
            return;
        }

        // The editor preview URL is optional in this iteration.
    }

    const debouncedPreview = debounce(function () {
        requestPreview().catch(function () {
            // Ignore preview failures in the first iteration.
        });
    }, 250);

    function applySelectedProperties() {
        if (!state.selectedLayer || !state.config) {
            return;
        }
        const section = sectionForLayer(state.selectedLayer);
        if (!section) {
            return;
        }

        const frame = {
            x: Number(propX.value || 0),
            y: Number(propY.value || 0),
            width: Number(propWidth.value || 50),
            height: Number(propHeight.value || 50),
        };
        applyFrameToSection(state.selectedLayer, section, frame, state.config.carta || {});
        applyAdvancedProperties(state.selectedLayer, section);
        renderLayers();
        debouncedPreview();
    }

    function syncLayerFromElement(target) {
        const layerName = target.dataset.layer;
        const section = sectionForLayer(layerName);
        if (!section) {
            return;
        }
        const frame = getFrameFromElement(target);
        applyFrameToSection(layerName, section, frame, state.config.carta || {});
        setActiveLayer(layerName);
        debouncedPreview();
    }

    function setupInteract() {
        if (!window.interact) {
            return;
        }

        window.interact('.layout-layer').draggable({
            listeners: {
                move: function (event) {
                    const target = event.target;
                    const left = (Number(target.style.left.replace('px', '')) || 0) + event.dx;
                    const top = (Number(target.style.top.replace('px', '')) || 0) + event.dy;
                    target.style.left = Math.max(0, Math.round(left)) + 'px';
                    target.style.top = Math.max(0, Math.round(top)) + 'px';
                },
                end: function (event) {
                    syncLayerFromElement(event.target);
                },
            },
        }).resizable({
            edges: { left: true, right: true, bottom: true, top: true },
            listeners: {
                move: function (event) {
                    const target = event.target;
                    const width = Math.max(20, event.rect.width);
                    const height = Math.max(20, event.rect.height);
                    const left = (Number(target.style.left.replace('px', '')) || 0) + event.deltaRect.left;
                    const top = (Number(target.style.top.replace('px', '')) || 0) + event.deltaRect.top;

                    target.style.width = Math.round(width) + 'px';
                    target.style.height = Math.round(height) + 'px';
                    target.style.left = Math.max(0, Math.round(left)) + 'px';
                    target.style.top = Math.max(0, Math.round(top)) + 'px';
                },
                end: function (event) {
                    syncLayerFromElement(event.target);
                },
            },
            modifiers: [
                window.interact.modifiers.restrictSize({
                    min: { width: 20, height: 20 },
                }),
            ],
        });
    }

    async function createLayout() {
        const name = window.prompt('Nombre del nuevo layout');
        if (!name) {
            return;
        }

        const response = await fetch('/layouts/api/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                card_type: state.cardType,
                name: name,
            }),
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || 'No se pudo crear layout');
        }

        state.layouts.push(payload.layout);
        state.activeLayoutId = payload.layout.id;
        refreshLayoutSelect();
        renderLayers();
        setStatus('Layout creado');
    }

    async function renameLayout() {
        if (!state.activeLayoutId) {
            return;
        }
        const active = getActiveLayout();
        const name = window.prompt('Nuevo nombre', active ? active.name : '');
        if (!name) {
            return;
        }

        const response = await fetch('/layouts/api/rename', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                layout_id: state.activeLayoutId,
                name: name,
            }),
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || 'No se pudo renombrar');
        }

        const index = state.layouts.findIndex(function (layout) {
            return layout.id === state.activeLayoutId;
        });
        if (index >= 0) {
            state.layouts[index] = payload.layout;
        }
        refreshLayoutSelect();
        setStatus('Layout renombrado');
    }

    async function deleteLayout() {
        if (!state.activeLayoutId) {
            return;
        }
        if (!window.confirm('Borrar layout seleccionado?')) {
            return;
        }

        const response = await fetch('/layouts/api/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                layout_id: state.activeLayoutId,
            }),
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || 'No se pudo borrar');
        }

        state.layouts = state.layouts.filter(function (layout) {
            return layout.id !== state.activeLayoutId;
        });
        state.activeLayoutId = state.layouts[0] ? state.layouts[0].id : null;
        refreshLayoutSelect();
        renderLayers();
        setStatus('Layout borrado');
    }

    async function setDefaultLayout() {
        if (!state.activeLayoutId) {
            return;
        }

        const response = await fetch('/layouts/api/set-default', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                layout_id: state.activeLayoutId,
            }),
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || 'No se pudo actualizar default');
        }

        state.layouts = state.layouts.map(function (layout) {
            const updated = Object.assign({}, layout);
            updated.is_default = layout.id === payload.layout.id;
            return updated;
        });
        refreshLayoutSelect();
        setStatus('Default actualizado');
    }

    layoutSelect.addEventListener('change', function () {
        const selected = Number(layoutSelect.value);
        state.activeLayoutId = Number.isNaN(selected) ? null : selected;
        state.selectedLayer = null;
        renderLayers();
    });

    cardTypeSelect.addEventListener('change', function () {
        state.cardType = cardTypeSelect.value;
        fetchLayoutsByCardType(state.cardType).catch(function (error) {
            setStatus(error.message, 'error');
        });
    });

    applyButton.addEventListener('click', function () {
        applySelectedProperties();
    });

    document.getElementById('layout-save').addEventListener('click', function () {
        saveConfig().catch(function (error) {
            setStatus(error.message, 'error');
        });
    });
    document.getElementById('layout-create').addEventListener('click', function () {
        createLayout().catch(function (error) {
            setStatus(error.message, 'error');
        });
    });
    document.getElementById('layout-rename').addEventListener('click', function () {
        renameLayout().catch(function (error) {
            setStatus(error.message, 'error');
        });
    });
    document.getElementById('layout-delete').addEventListener('click', function () {
        deleteLayout().catch(function (error) {
            setStatus(error.message, 'error');
        });
    });
    document.getElementById('layout-set-default').addEventListener('click', function () {
        setDefaultLayout().catch(function (error) {
            setStatus(error.message, 'error');
        });
    });

    cardTypeSelect.value = state.cardType;
    refreshLayoutSelect();
    renderLayers();
    setupInteract();
})();
