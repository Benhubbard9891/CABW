"""
Three.js-based 3D Visualization Renderer

Generates HTML/JS for real-time 3D visualization of the simulation.
"""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VizConfig:
    """Configuration for 3D visualization."""
    width: int = 1200
    height: int = 800
    background_color: str = "#1a1a2e"
    grid_color: str = "#333344"
    agent_colors: dict[str, str] = field(default_factory=lambda: {
        'default': '#4CAF50',
        'leader': '#FFD700',
        'injured': '#FF5722',
        'dead': '#666666'
    })
    show_emotions: bool = True
    show_paths: bool = True
    show_zones: bool = True
    camera_position: tuple[float, float, float] = (50, 50, 100)
    follow_agent: str | None = None


class ThreeJSRenderer:
    """
    Generate Three.js HTML/JS for 3D simulation visualization.
    """

    def __init__(self, config: VizConfig | None = None):
        self.config = config or VizConfig()
        self.frame_count = 0

    def generate_html(self, simulation_state: dict[str, Any]) -> str:
        """
        Generate complete HTML page with Three.js visualization.
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CABW Simulation Visualization</title>
    <style>
        body {{
            margin: 0;
            overflow: hidden;
            background: {self.config.background_color};
            font-family: 'Segoe UI', sans-serif;
        }}
        #canvas-container {{
            width: 100vw;
            height: 100vh;
        }}
        #info-panel {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 15px;
            border-radius: 8px;
            max-width: 300px;
        }}
        #controls {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 10px;
            border-radius: 8px;
        }}
        .agent-label {{
            position: absolute;
            color: white;
            font-size: 12px;
            pointer-events: none;
            text-shadow: 1px 1px 2px black;
        }}
        button {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 4px;
            border-radius: 4px;
            cursor: pointer;
        }}
        button:hover {{
            background: #45a049;
        }}
    </style>
</head>
<body>
    <div id="canvas-container"></div>
    <div id="info-panel">
        <h3>CABW Simulation</h3>
        <p>Tick: <span id="tick">0</span></p>
        <p>Agents: <span id="agent-count">0</span></p>
        <p>Weather: <span id="weather">-</span></p>
        <div id="selected-agent"></div>
    </div>
    <div id="controls">
        <button onclick="togglePaths()">Toggle Paths</button>
        <button onclick="toggleEmotions()">Toggle Emotions</button>
        <button onclick="resetCamera()">Reset Camera</button>
        <button onclick="togglePause()">Pause/Play</button>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        // Simulation state
        const simState = {json.dumps(simulation_state)};

        // Three.js setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color('{self.config.background_color}');
        scene.fog = new THREE.Fog('{self.config.background_color}', 50, 200);

        const camera = new THREE.PerspectiveCamera(
            75,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        camera.position.set({self.config.camera_position[0]}, {self.config.camera_position[1]}, {self.config.camera_position[2]});

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.getElementById('canvas-container').appendChild(renderer.domElement);

        // Controls
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(50, 100, 50);
        directionalLight.castShadow = true;
        scene.add(directionalLight);

        // Grid
        const gridHelper = new THREE.GridHelper(100, 100, 0x444444, 0x222222);
        scene.add(gridHelper);

        // Ground plane
        const groundGeometry = new THREE.PlaneGeometry(200, 200);
        const groundMaterial = new THREE.MeshLambertMaterial({{
            color: 0x1a1a2e,
            transparent: true,
            opacity: 0.5
        }});
        const ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = -0.1;
        scene.add(ground);

        // Agent meshes
        const agents = {{}};
        const agentPaths = {{}};
        const agentLabels = {{}};

        // Agent geometry
        const agentGeometry = new THREE.SphereGeometry(1, 16, 16);

        // Create agents
        function createAgent(agentId, agentData) {{
            const color = agentData.color || '{self.config.agent_colors['default']}';
            const material = new THREE.MeshPhongMaterial({{
                color: color,
                emissive: color,
                emissiveIntensity: 0.2
            }});
            const mesh = new THREE.Mesh(agentGeometry, material);
            mesh.castShadow = true;
            mesh.userData = {{ agentId: agentId, ...agentData }};

            // Position
            const loc = agentData.location || [0, 0];
            mesh.position.set(loc[0], 1, loc[1]);

            // Emotion indicator
            if ({str(self.config.show_emotions).lower()}) {{
                const emotionColor = getEmotionColor(agentData.emotional_state);
                const indicatorGeometry = new THREE.RingGeometry(1.2, 1.5, 16);
                const indicatorMaterial = new THREE.MeshBasicMaterial({{
                    color: emotionColor,
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.6
                }});
                const indicator = new THREE.Mesh(indicatorGeometry, indicatorMaterial);
                indicator.rotation.x = -Math.PI / 2;
                indicator.position.y = 0.1;
                mesh.add(indicator);
                mesh.userData.emotionIndicator = indicator;
            }}

            scene.add(mesh);
            agents[agentId] = mesh;

            // Path line
            if ({str(self.config.show_paths).lower()}) {{
                const pathMaterial = new THREE.LineBasicMaterial({{
                    color: color,
                    transparent: true,
                    opacity: 0.3
                }});
                const pathGeometry = new THREE.BufferGeometry();
                const pathLine = new THREE.Line(pathGeometry, pathMaterial);
                scene.add(pathLine);
                agentPaths[agentId] = {{ line: pathLine, points: [] }};
            }}

            return mesh;
        }}

        function getEmotionColor(emotionalState) {{
            if (!emotionalState) return 0x888888;
            const dominant = emotionalState.dominant || 'neutral';
            const colors = {{
                'joy': 0xFFD700,
                'sadness': 0x4169E1,
                'anger': 0xDC143C,
                'fear': 0x800080,
                'surprise': 0xFFA500,
                'neutral': 0x888888
            }};
            return colors[dominant] || 0x888888;
        }}

        // Initialize agents from state
        if (simState.agents) {{
            for (const [agentId, agentData] of Object.entries(simState.agents)) {{
                createAgent(agentId, agentData);
            }}
        }}

        // Update info panel
        function updateInfoPanel() {{
            document.getElementById('tick').textContent = simState.tick || 0;
            document.getElementById('agent-count').textContent =
                Object.keys(simState.agents || {{}}).length;
            document.getElementById('weather').textContent =
                simState.environment?.weather?.type || '-';
        }}

        updateInfoPanel();

        // Animation loop
        let isPaused = false;

        function animate() {{
            requestAnimationFrame(animate);

            if (!isPaused) {{
                controls.update();

                // Animate agents
                for (const [agentId, mesh] of Object.entries(agents)) {{
                    // Bobbing animation
                    mesh.position.y = 1 + Math.sin(Date.now() * 0.003 + agentId.charCodeAt(0)) * 0.2;

                    // Rotate emotion indicator
                    if (mesh.userData.emotionIndicator) {{
                        mesh.userData.emotionIndicator.rotation.z += 0.01;
                    }}
                }}
            }}

            renderer.render(scene, camera);
        }}

        animate();

        // Handle window resize
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});

        // Click to select agent
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        window.addEventListener('click', (event) => {{
            mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(Object.values(agents));

            if (intersects.length > 0) {{
                const agent = intersects[0].object;
                showAgentDetails(agent.userData);
            }}
        }});

        function showAgentDetails(agentData) {{
            const panel = document.getElementById('selected-agent');
            panel.innerHTML = `
                <hr>
                <h4>Agent: ${{agentData.agentId}}</h4>
                <p>Health: ${{agentData.health || '?'}}</p>
                <p>Emotion: ${{agentData.emotional_state?.dominant || '?'}}</p>
                <p>Action: ${{agentData.current_action || 'None'}}</p>
            `;
        }}

        // Control functions
        function togglePaths() {{
            for (const path of Object.values(agentPaths)) {{
                path.line.visible = !path.line.visible;
            }}
        }}

        function toggleEmotions() {{
            for (const agent of Object.values(agents)) {{
                if (agent.userData.emotionIndicator) {{
                    agent.userData.emotionIndicator.visible =
                        !agent.userData.emotionIndicator.visible;
                }}
            }}
        }}

        function resetCamera() {{
            camera.position.set({self.config.camera_position[0]}, {self.config.camera_position[1]}, {self.config.camera_position[2]});
            controls.target.set(0, 0, 0);
            controls.update();
        }}

        function togglePause() {{
            isPaused = !isPaused;
        }}

        // WebSocket for real-time updates
        const ws = new WebSocket(`ws://${{window.location.host}}/simulation/${{simState.sim_id || 'default'}}/ws`);

        ws.onmessage = (event) => {{
            const data = JSON.parse(event.data);
            if (data.type === 'tick_update') {{
                updateAgentPositions(data.data.agents);
                document.getElementById('tick').textContent = data.tick;
            }}
        }};

        function updateAgentPositions(newAgents) {{
            for (const [agentId, agentData] of Object.entries(newAgents)) {{
                if (agents[agentId]) {{
                    const mesh = agents[agentId];
                    const loc = agentData.location;
                    mesh.position.x = loc[0];
                    mesh.position.z = loc[1];

                    // Update path
                    if (agentPaths[agentId]) {{
                        agentPaths[agentId].points.push(new THREE.Vector3(loc[0], 0.1, loc[1]));
                        if (agentPaths[agentId].points.length > 50) {{
                            agentPaths[agentId].points.shift();
                        }}
                        agentPaths[agentId].line.geometry.setFromPoints(
                            agentPaths[agentId].points
                        );
                    }}
                }}
            }}
        }}
    </script>
</body>
</html>"""

    def update_state(self, simulation_state: dict[str, Any]) -> str:
        """
        Generate JavaScript to update visualization state.
        """
        return f"""
        <script>
            // Update simulation state
            const newState = {json.dumps(simulation_state)};

            // Update agents
            for (const [agentId, agentData] of Object.entries(newState.agents || {{}})) {{
                if (agents[agentId]) {{
                    const mesh = agents[agentId];
                    const loc = agentData.location;
                    mesh.position.x = loc[0];
                    mesh.position.z = loc[1];

                    // Update emotion indicator
                    if (mesh.userData.emotionIndicator) {{
                        mesh.userData.emotionIndicator.material.color.setHex(
                            getEmotionColor(agentData.emotional_state)
                        );
                    }}
                }}
            }}

            // Update info panel
            document.getElementById('tick').textContent = newState.tick || 0;
        </script>
        """

    def export_static(self, filepath: str, simulation_state: dict[str, Any]):
        """Export static HTML file."""
        html = self.generate_html(simulation_state)
        with open(filepath, 'w') as f:
            f.write(html)
        return filepath
