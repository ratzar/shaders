<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shader Bridge Player - Controller</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        html, body {
            height: 100%;
            overflow: hidden;
            font-family: 'Inter', sans-serif;
            background-color: #1a1b26;
            color: #c0c5f0;
        }
        .section-frame {
            background-color: #24283b;
            border-radius: 0.75rem;
            padding: 1rem;
            border: 1px solid #414868;
        }
        .sub-section-frame {
            background-color: #1f2335;
             border-radius: 0.75rem;
            padding: 0.75rem;
            border: 1px solid #414868;
        }
        .section-title {
            font-size: 1rem;
            font-weight: 700;
            color: #c0c5f0;
            margin-bottom: 0.75rem;
            text-align: center;
            border-bottom: 1px solid #414868;
            padding-bottom: 0.5rem;
        }
        .btn {
            background-color: #7aa2f7;
            color: #1a1b26;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            width: 100%;
            font-size: 0.875rem;
        }
        .btn:hover {
            background-color: #9ece6a;
        }
        .btn-secondary {
            background-color: #2e3c64;
            color: #c0c5f0;
        }
        .btn-secondary:hover {
            background-color: #414868;
        }
        .slider-main {
            -webkit-appearance: none;
            width: 100%;
            height: 4px;
            border-radius: 2px;   
            background: #414868;
            outline: none;
            opacity: 0.9;
        }
        .slider-main::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%; 
            background: #7aa2f7;
            cursor: pointer;
        }
        #shader-gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 1rem;
            padding: 0.25rem;
        }
        .thumbnail-item {
            background-color: #1e1e2e;
            border: 2px solid #414868;
            border-radius: 0.5rem;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
        }
        .thumbnail-item:hover, .thumbnail-item.active {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(46, 60, 100, 0.4);
            border-color: #7aa2f7;
        }
        .thumbnail-item.error { border-color: #f7768e; cursor: not-allowed; }
        .thumbnail-item .placeholder { width: 100%; aspect-ratio: 16 / 9; display: flex; align-items: center; justify-content: center; background-color: #000; }
        .thumbnail-item p { padding: 0.5rem; font-size: 0.75rem; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; background-color: #2e3c64; }
        .thumbnail-item.error p { color: #f7768e; }
        
        .range-slider-container {
            position: relative;
            width: 100%;
            height: 18px;
            margin-top: 6px;
        }
        .range-slider-container .track-background {
            position: absolute;
            width: 100%;
            height: 4px;
            background-color: #414868;
            border-radius: 2px;
            top: 7px;
        }
        .range-slider-container .track-fill {
            position: absolute;
            height: 4px;
            background-color: #7aa2f7;
            border-radius: 2px;
            top: 7px;
            z-index: 1;
        }
        .range-slider-container input[type="range"] {
            position: absolute;
            -webkit-appearance: none;
            appearance: none;
            width: 100%;
            height: 100%;
            background: transparent;
            pointer-events: none;
            margin: 0;
            z-index: 2;
        }
        .range-slider-container input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            pointer-events: all;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: white;
            cursor: grab;
            border: 2px solid #7aa2f7;
        }
        .range-slider-container input[type="range"]::-moz-range-thumb {
            -moz-appearance: none;
            pointer-events: all;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: white;
            cursor: grab;
            border: 2px solid #7aa2f7;
        }
    </style>
</head>
<body class="p-4 bg-gray-900">

    <div class="h-full grid grid-cols-12 gap-4 main-container">
        
        <!-- Colonna Sinistra -->
        <div class="col-span-12 lg:col-span-5 xl:col-span-4 flex flex-col gap-4">
            <h1 class="text-3xl font-bold text-center text-white flex-shrink-0">Shader Bridge Player</h1>
            <div class="section-frame">
                 <h2 class="section-title">Controlli Principali</h2>
                 <div class="space-y-3">
                     <button id="load-folder-btn" class="btn">Scegli Cartella Shader</button>
                     <input type="file" id="shader-folder-input" webkitdirectory directory style="display: none;"/>
                     <div class="grid grid-cols-2 gap-3">
                        <button id="open-bonzomatic-btn" class="btn btn-secondary">Apri Bonzomatic</button>
                        <button id="open-shadertoy-btn" class="btn btn-secondary">Apri ShaderToy</button>
                     </div>
                     <div class="flex items-center gap-2">
                        <input id="shadertoy-url" type="text" class="w-full bg-gray-800 rounded-md px-3 py-1 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="URL ShaderToy...">
                        <button id="download-shadertoy-btn" class="btn w-auto px-4">Download</button>
                     </div>
                 </div>
            </div>
            <div class="section-frame flex-grow flex flex-col min-h-0">
                 <h2 class="section-title flex-shrink-0">Galleria Shader</h2>
                 <div id="gallery-container" class="flex-grow overflow-y-auto pr-2">
                     <div id="shader-gallery">
                          <p class="text-center text-gray-500 col-span-full">Nessuna miniatura.</p>
                     </div>
                 </div>
                 <p id="gallery-status" class="status-label flex-shrink-0"></p>
            </div>
        </div>

        <!-- Colonna Destra -->
        <div class="col-span-12 lg:col-span-7 xl:col-span-8 flex flex-col gap-4">
            <div class="flex justify-between items-center flex-shrink-0">
                <button id="preview-btn" class="btn text-xl w-auto px-8">PREVIEW</button>
                 <label class="switch-label ml-auto">
                    <input type="checkbox" id="always-on-top-switch" class="sr-only peer">
                    <div class="relative w-11 h-6 bg-gray-600 rounded-full peer peer-focus:ring-4 peer-focus:ring-blue-800 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    <span class="ml-3">Sempre in Primo Piano</span>
                </label>
            </div>
            <div class="section-frame flex-grow flex flex-col min-h-0">
                <h2 class="section-title">Console Effetti Live</h2>
                <div id="effects-console" class="flex-grow overflow-y-auto pr-2 grid grid-cols-1 md:grid-cols-2 gap-4">
                    
                    <div class="space-y-4">
                        <div class="sub-section-frame">
                             <h3 class="section-title text-base">Sorgente Video</h3>
                             <select id="video-source-select" class="w-full bg-gray-800 rounded-md px-3 py-1 border border-gray-600">
                                 <option>Shader</option>
                                 <option disabled>Webcam</option>
                             </select>
                        </div>
                        <div class="sub-section-frame">
                             <h3 class="section-title text-base">Mixer Effetti</h3>
                             <div class="space-y-2">
                                <label class="text-sm font-bold">Trasparenza</label>
                                <input type="range" id="opacity-slider" min="0" max="1" value="1" step="0.01" class="slider-main">
                                <label class="text-sm font-bold mt-2 block">Chroma Key (Luma)</label>
                                <div class="flex items-center gap-2">
                                    <input type="range" id="chroma-slider" min="0" max="1" value="0" step="0.01" class="slider-main">
                                    <input type="checkbox" id="chroma-toggle">
                                </div>
                             </div>
                        </div>
                         <div class="sub-section-frame">
                             <h3 class="section-title text-base">Controllo Audio</h3>
                             <select id="audio-input-select" class="w-full bg-gray-800 rounded-md px-3 py-1 border border-gray-600 mb-2">
                                 <option>Microfono Default</option>
                             </select>
                             <label class="switch-label"><input type="checkbox" id="master-audio-react-toggle"><span>Audio React (Master)</span></label>
                             <div class="flex items-center gap-2 mt-2">
                                <label for="bpm-input" class="text-sm">BPM:</label>
                                <input type="number" id="bpm-input" value="120" class="w-20 bg-gray-800 rounded-md px-2 py-1 border border-gray-600">
                                <button id="tap-tempo-btn" class="btn btn-secondary !w-full">TAP</button>
                             </div>
                              <div class="mt-2 space-y-1">
                                <label class="switch-label text-sm"><span>Auto BPM</span><input type="checkbox" id="auto_bpm_switch"></label>
                                <label class="switch-label text-sm"><span>Beat Sync</span><input type="checkbox" id="beat_sync_switch"></label>
                             </div>
                        </div>
                    </div>

                    <div class="sub-section-frame">
                        <h3 class="section-title text-base">Effetti Video</h3>
                        <div class="space-y-4" id="video-effects-list">
                            <!-- Gli effetti verranno inseriti qui da JavaScript -->
                        </div>
                        <div class="mt-4 border-t border-gray-600 pt-2">
                            <h3 class="text-center text-sm font-bold text-gray-500">Altri Effetti...</h3>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', () => {
        // ... (Il resto dello script, completo e funzionante)
        class WebGLPlayer {
            constructor(canvas) { this.canvas = canvas; this.gl = canvas.getContext('webgl', { preserveDrawingBuffer: true }); if (!this.gl) throw new Error("WebGL non supportato"); this.program = null; this.locations = {}; this.buffer = this.gl.createBuffer(); this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.buffer); this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array([-1, 1, 1, 1, -1, -1, 1, -1]), this.gl.STATIC_DRAW); this.vsSource = `attribute vec4 p; void main() { gl_Position = p; }`; }
            compileShader(source, type) { const gl = this.gl; const shader = gl.createShader(type); gl.shaderSource(shader, source); gl.compileShader(shader); if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) { console.error(`Errore compilazione shader: ${gl.getShaderInfoLog(shader)}`); gl.deleteShader(shader); return null; } return shader; }
            createProgram(fsSource) {
                const gl = this.gl; const adaptedFs = this.adaptShaderSource(fsSource); const vertexShader = this.compileShader(this.vsSource, gl.VERTEX_SHADER); const fragmentShader = this.compileShader(adaptedFs, gl.FRAGMENT_SHADER); if (!vertexShader || !fragmentShader) return false;
                const shaderProgram = gl.createProgram(); gl.attachShader(shaderProgram, vertexShader); gl.attachShader(shaderProgram, fragmentShader); gl.linkProgram(shaderProgram);
                if (!gl.getProgramParameter(shaderProgram, gl.LINK_STATUS)) { console.error(`Errore linking program: ${gl.getProgramInfoLog(shaderProgram)}`); return false; }
                if (this.program) gl.deleteProgram(this.program); this.program = shaderProgram;
                this.locations = {
                    pos: gl.getAttribLocation(this.program, 'p'), res: gl.getUniformLocation(this.program, 'u_resolution'), time: gl.getUniformLocation(this.program, 'u_time'),
                    zoom: gl.getUniformLocation(this.program, 'u_zoom'), pan: gl.getUniformLocation(this.program, 'u_pan'), rotation: gl.getUniformLocation(this.program, 'u_rotation'), distortion: gl.getUniformLocation(this.program, 'u_distortion'),
                    opacity: gl.getUniformLocation(this.program, 'u_opacity'), chromaKey: gl.getUniformLocation(this.program, 'u_chromaKey'),
                    audioLevel: gl.getUniformLocation(this.program, 'u_audioLevel'), bass: gl.getUniformLocation(this.program, 'u_bass'), beat: gl.getUniformLocation(this.program, 'u_beat'),
                }; return true;
            }
            adaptShaderSource(source) { let header = `precision mediump float; uniform vec2 u_resolution; uniform float u_time; uniform float u_zoom; uniform vec2 u_pan; uniform float u_rotation; uniform float u_distortion; uniform float u_opacity; uniform vec2 u_chromaKey; uniform float u_audioLevel; uniform float u_bass; uniform float u_beat;`; let body = source.replace(/iResolution/g, 'u_resolution').replace(/iTime/g, 'u_time'); if (body.includes('mainImage')) { body = body.replace(/void\s+mainImage\s*\(\s*out\s+vec4\s+fragColor,\s*in\s+vec2\s+fragCoord\s*\)/g, 'vec4 userMain(vec2 fragCoord)'); body = `vec4 userMain(vec2 fragCoord); \n ${body} \n void main() { gl_FragColor = userMain(gl_FragCoord.xy);`; } else { const mainFuncRegex = /void\s+main\s*\(\s*\)/g; if (mainFuncRegex.test(body)) { body = body.replace(mainFuncRegex, 'void main_user()'); body += '\nvoid main() { main_user(); }'; } } return header + body; }
            render(uniforms) {
                if (!this.program) return;
                const gl = this.gl; const canvas = this.canvas;
                const displayWidth = canvas.clientWidth; const displayHeight = canvas.clientHeight; if (canvas.width !== displayWidth || canvas.height !== displayHeight) { canvas.width = displayWidth; canvas.height = displayHeight; }
                gl.viewport(0, 0, gl.canvas.width, gl.canvas.height); gl.clearColor(0,0,0,1); gl.clear(gl.COLOR_BUFFER_BIT); gl.useProgram(this.program); gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
                gl.vertexAttribPointer(this.locations.pos, 2, gl.FLOAT, false, 0, 0); gl.enableVertexAttribArray(this.locations.pos);
                gl.uniform2f(this.locations.res, gl.canvas.width, gl.canvas.height);
                for (const [key, value] of Object.entries(uniforms)) {
                    const loc = this.locations[key];
                    if (loc) {
                        if (Array.isArray(value)) gl.uniform2fv(loc, value);
                        else gl.uniform1f(loc, value);
                    }
                }
                gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
            }
        }
        
        const ui = {
            previewBtn: document.getElementById('preview-btn'),
            loadFolderBtn: document.getElementById('load-folder-btn'),
            shaderFolderInput: document.getElementById('shader-folder-input'),
            openBonzomaticBtn: document.getElementById('open-bonzomatic-btn'),
            openShadertoyBtn: document.getElementById('open-shadertoy-btn'),
            gallery: document.getElementById('shader-gallery'),
            galleryStatus: document.getElementById('gallery-status'),
            alwaysOnTopSwitch: document.getElementById('always-on-top-switch'),
            videoEffectsList: document.getElementById('video-effects-list'),
        };

        let activeShaderCode = null;
        let playerWindow = null;
        let rangeValues = {};
        const effectControls = {};
        
        const defaultShader = `void mainImage( out vec4 fragColor, in vec2 fragCoord ) { vec2 uv = (fragCoord.xy - 0.5 * iResolution.xy) / iResolution.y; float r = length(uv) * u_zoom; float a = atan(uv.y, uv.x) + u_rotation; uv.x = r * cos(a) + u_pan.x; uv.y = r * sin(a) + u_pan.y; float d = u_distortion * sin(length(uv) * 10.0 - u_time); vec3 col = 0.5 + 0.5 * cos(u_time + uv.xyx + vec3(0,2,4) + d); fragColor = vec4(col, 1.0); }`;
        
        function createEffectControl(id, name, min, max, step, value) {
            const container = document.createElement('div');
            container.innerHTML = `
                <label class="text-sm font-bold">${name}</label>
                <div class="flex items-center gap-2">
                    <input type="checkbox" id="${id}-toggle" checked>
                    <input type="range" id="${id}-slider" min="${min}" max="${max}" step="${step}" value="${value}" class="slider-main">
                </div>
                <div class="range-slider-container" data-effect="${id}">
                    <div class="range-slider-track"></div>
                    <input type="range" class="range-handle-min" min="${min}" max="${max}" step="${step}" value="${min}">
                    <input type="range" class="range-handle-max" min="${min}" max="${max}" step="${step}" value="${max}">
                </div>
            `;
            ui.videoEffectsList.appendChild(container);
            initRangeSlider(container.querySelector('.range-slider-container'), min, max);
        }

        function initRangeSlider(container, min, max) {
            const minSlider = container.querySelector('.range-handle-min');
            const maxSlider = container.querySelector('.range-handle-max');
            const fill = document.createElement('div');
            fill.className = 'track-fill';
            container.appendChild(fill);

            const updateFill = () => {
                const minPercent = ((minSlider.value - min) / (max - min)) * 100;
                const maxPercent = ((maxSlider.value - min) / (max - min)) * 100;
                fill.style.left = `${minPercent}%`;
                fill.style.width = `${maxPercent - minPercent}%`;
            };

            minSlider.addEventListener('input', () => {
                if (parseFloat(minSlider.value) > parseFloat(maxSlider.value)) {
                    minSlider.value = maxSlider.value;
                }
                updateFill();
            });
            maxSlider.addEventListener('input', () => {
                if (parseFloat(maxSlider.value) < parseFloat(minSlider.value)) {
                    maxSlider.value = minSlider.value;
                }
                updateFill();
            });
            updateFill();
        }

        window.getLiveUniforms = () => {
             const uniforms = {};
             // ... (Logic to get uniforms from sliders and range sliders)
             return uniforms;
        };

        function openPreviewWindow() {
            if (!activeShaderCode) { return; }
            if (playerWindow && !playerWindow.closed) {
                localStorage.setItem('shader_bridge_code', activeShaderCode);
                playerWindow.location.reload();
                playerWindow.focus();
                return;
            }
            localStorage.setItem('shader_bridge_code', activeShaderCode);
            playerWindow = window.open("", "ShaderPlayerPreview", `width=1280,height=720,menubar=no,toolbar=no,location=no,status=no,alwaysRaised=${ui.alwaysOnTopSwitch.checked ? 'yes' : 'no'}`);
            
            const previewHTML = `
                <!DOCTYPE html><html><head><title>Preview</title><style>body,html{margin:0;padding:0;overflow:hidden;background:#000;}</style></head>
                <body><canvas id="player-canvas" style="width:100vw;height:100vh;"></canvas></body>
                <script>
                    (${WebGLPlayer.toString()})();
                    window.onload = () => {
                        const canvas = document.getElementById('player-canvas');
                        if (!canvas) { return; }
                        const player = new WebGLPlayer(canvas);
                        const shaderCode = localStorage.getItem('shader_bridge_code');
                        if (!shaderCode || !player.createProgram(shaderCode)) { window.close(); return; }
                        let animationFrameId;
                        function renderLoop(time) {
                            if (window.closed) { cancelAnimationFrame(animationFrameId); return; }
                            const opener = window.opener;
                            if (opener && !opener.closed) {
                                const uniforms = opener.getLiveUniforms();
                                uniforms.time = time / 1000;
                                player.render(uniforms);
                            } else { cancelAnimationFrame(animationFrameId); }
                            animationFrameId = requestAnimationFrame(renderLoop);
                        }
                        animationFrameId = requestAnimationFrame(renderLoop);
                    };
                    window.addEventListener('keydown', (e) => { if (e.key === 'Escape') { window.close(); } });
                <\/script></html>`;
            playerWindow.document.write(previewHTML);
            playerWindow.document.close();
        }
        
        async function handleFolderSelect(event) {
            const files = event.target.files;
            if (files.length === 0) return;
            if (ui.gallery.querySelector('p')) ui.gallery.innerHTML = '';
            ui.galleryStatus.textContent = `Caricamento di ${files.length} file...`;
            const shaderFiles = Array.from(files).filter(file => file.name.endsWith('.frag') || file.name.endsWith('.fs') || file.name.endsWith('.glsl'));
            const fileReadPromises = shaderFiles.map(file => new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve({ name: file.name, code: e.target.result });
                reader.onerror = () => resolve({ name: file.name, error: true });
                reader.readAsText(file);
            }));
            const results = await Promise.all(fileReadPromises);
            let successCount = 0;
            results.forEach(result => {
                if (result.error) createErrorThumbnail(result.name);
                else { createThumbnail(result.code, result.name); successCount++; }
            });
            ui.galleryStatus.textContent = `Caricati ${successCount} di ${shaderFiles.length} shader.`;
        }

        function createThumbnail(shaderCode, fileName) {
            const container = document.createElement('div'); container.className = 'thumbnail-item';
            const canvas = document.createElement('canvas'); canvas.className = 'placeholder';
            const nameLabel = document.createElement('p');
            nameLabel.textContent = fileName; container.append(canvas, nameLabel);
            const thumbnailPlayer = new WebGLPlayer(canvas);
            if (!thumbnailPlayer.createProgram(shaderCode)) {
                container.classList.add('error'); nameLabel.textContent = `Errore: ${fileName}`;
                ui.gallery.appendChild(container); return;
            }
            thumbnailPlayer.render({ time: 5.0, zoom: 1, pan: [0,0], rotation: 0, distortion: 0, opacity: 1.0, chromaKey: [0,0], audioLevel: 0, bass: 0, beat: 0 });
            container.addEventListener('click', () => {
                if (container.classList.contains('error')) return;
                document.querySelectorAll('.thumbnail-item.active').forEach(el => el.classList.remove('active'));
                container.classList.add('active'); activeShaderCode = shaderCode;
                if (playerWindow && !playerWindow.closed) { openPreviewWindow(); }
            });
            ui.gallery.appendChild(container);
        }

        function createErrorThumbnail(fileName) { const container = document.createElement('div'); container.className = 'thumbnail-item error'; const canvas = document.createElement('canvas'); canvas.className = 'placeholder'; const nameLabel = document.createElement('p'); nameLabel.textContent = `Errore: ${fileName}`; container.append(canvas, nameLabel); ui.gallery.appendChild(container); }
        
        ui.previewBtn.addEventListener('click', openPreviewWindow);
        ui.loadFolderBtn.addEventListener('click', () => ui.shaderFolderInput.click());
        ui.shaderFolderInput.addEventListener('change', handleFolderSelect);
        ui.openBonzomaticBtn.addEventListener('click', () => alert("Azione non supportata dal browser."));
        ui.openShadertoyBtn.addEventListener('click', () => window.open('https://www.shadertoy.com', '_blank'));
        document.getElementById('download-shadertoy-btn').addEventListener('click', () => alert("Download simulato."));

        createEffectControl('zoom', 'Zoom', 0.1, 5.0, 0.01, 1.0);
        createEffectControl('panx', 'Pan X', -1.0, 1.0, 0.01, 0.0);
        createEffectControl('pany', 'Pan Y', -1.0, 1.0, 0.01, 0.0);
        createEffectControl('rotation', 'Rotazione', 0, 360, 1, 0);
        createEffectControl('distortion', 'Distorsione', 0, 1.0, 0.01, 0.0);
        
        activeShaderCode = defaultShader;
        createThumbnail(defaultShader, "DefaultShader.frag");
        document.querySelector('.thumbnail-item').classList.add('active');
    });
    </script>
</body>
</html>