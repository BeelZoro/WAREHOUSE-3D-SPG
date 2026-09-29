import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import random

st.set_page_config(page_title="WMS 3D - Central de Operações", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------
# ESTILIZAÇÃO CSS CUSTOMIZADA (DARK THEME MODERN)
# ---------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #1a1f2c;
        border: 1px solid #2e364f;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. GERAÇÃO DO ESTOQUE (ENDEREÇAMENTO GABARITO EXCEL)
# ---------------------------------------------------------
if "estoque" not in st.session_state:
    dados_iniciais = []
    niveis = [10, 20, 30]
    
    def get_pairs(start, count):
        return [(start + i*4, start + i*4 + 2) for i in range(count)]
    
    racks_c_trat = get_pairs(200, 4)   
    racks_c_geral = get_pairs(216, 15) 
    
    racks_b_trat = get_pairs(101, 4)   
    racks_b_geral = get_pairs(117, 14) 
    
    racks_a_trat = get_pairs(100, 4)   
    racks_a_geral = get_pairs(116, 14) 

    def montar_rua(nome_rua, lista_trat, lista_geral, z_pos, offset_geral):
        for idx, (pos_r, pos_l) in enumerate(lista_trat):
            col_idx = idx
            for nivel in niveis:
                dados_iniciais.append({
                    "id": f"{nome_rua}-{pos_r}-{nivel}", "rua": nome_rua, "pos_num": pos_r, "nivel": nivel,
                    "col_idx": col_idx, "side": "right", "z_pos": z_pos, "zona": "Tratativa",
                    "status": "Vazio", "etiqueta": "", "nota_fiscal": ""
                })
                dados_iniciais.append({
                    "id": f"{nome_rua}-{pos_l}-{nivel}", "rua": nome_rua, "pos_num": pos_l, "nivel": nivel,
                    "col_idx": col_idx, "side": "left", "z_pos": z_pos, "zona": "Tratativa",
                    "status": "Vazio", "etiqueta": "", "nota_fiscal": ""
                })
        
        for idx, (pos_r, pos_l) in enumerate(lista_geral):
            col_idx = idx + offset_geral
            for nivel in niveis:
                dados_iniciais.append({
                    "id": f"{nome_rua}-{pos_r}-{nivel}", "rua": nome_rua, "pos_num": pos_r, "nivel": nivel,
                    "col_idx": col_idx, "side": "right", "z_pos": z_pos, "zona": "Armazém",
                    "status": "Vazio", "etiqueta": "", "nota_fiscal": ""
                })
                dados_iniciais.append({
                    "id": f"{nome_rua}-{pos_l}-{nivel}", "rua": nome_rua, "pos_num": pos_l, "nivel": nivel,
                    "col_idx": col_idx, "side": "left", "z_pos": z_pos, "zona": "Armazém",
                    "status": "Vazio", "etiqueta": "", "nota_fiscal": ""
                })

    montar_rua("C", racks_c_trat, racks_c_geral, z_pos=-8.0, offset_geral=4)
    montar_rua("B", racks_b_trat, racks_b_geral, z_pos=-0.7, offset_geral=5)
    montar_rua("A", racks_a_trat, racks_a_geral, z_pos=0.7, offset_geral=5)

    st.session_state.estoque = pd.DataFrame(dados_iniciais)

df = st.session_state.estoque

# ---------------------------------------------------------
# 2. METRICAS / DASHBOARD DE CABEÇALHO
# ---------------------------------------------------------
st.title("🏭 WMS 3D - Central de Operações")

total_pos = len(df)
ocupados_total = len(df[df["status"] == "Ocupado"])
taxa_ocupacao = (ocupados_total / total_pos * 100) if total_pos > 0 else 0
ocupados_tratativa = len(df[(df["status"] == "Ocupado") & (df["zona"] == "Tratativa")])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total de Posições", total_pos)
m2.metric("Ocupação Geral", f"{taxa_ocupacao:.1f}%", f"{ocupados_total} paletes")
m3.metric("Tratativa Ocupada", f"{ocupados_tratativa} paletes")
m4.metric("Posições Livres", total_pos - ocupados_total)

st.divider()

# ---------------------------------------------------------
# 3. PAINEL LATERAL (ALOCAÇÃO MANUAL + MOCK DATA)
# ---------------------------------------------------------
st.sidebar.title("📦 Alocação de Carga")
st.sidebar.markdown("Use este painel para alocar paletes individualmente.")

col_rua, col_pos = st.sidebar.columns(2)
rua_selecionada = col_rua.selectbox("Rua", ["A", "B", "C"])

posicoes_disponiveis = sorted(df[df["rua"] == rua_selecionada]["pos_num"].unique())
pos_selecionada = col_pos.selectbox("Posição", posicoes_disponiveis)

nivel_selecionado = st.sidebar.selectbox("Nível", [10, 20, 30])

id_alvo = f"{rua_selecionada}-{pos_selecionada}-{nivel_selecionado}"
idx_linha = df[df["id"] == id_alvo].index[0]
linha_atual = df.loc[idx_linha]

st.sidebar.divider()
st.sidebar.subheader(f"Endereço: {id_alvo}")
if linha_atual["zona"] == "Tratativa":
    st.sidebar.error("🚨 ÁREA DE TRATATIVA")
else:
    st.sidebar.success("✅ ARMAZÉM GERAL")

# FORMULÁRIO DE INSERÇÃO MANUAL
with st.sidebar.form("form_alocacao"):
    novo_status = st.radio("Status:", ["Vazio", "Ocupado"], index=0 if linha_atual["status"] == "Vazio" else 1)
    nova_etiqueta = st.text_input("Etiqueta Unitizadora:", value=linha_atual["etiqueta"], placeholder="Ex: PAL-1234")
    nova_nf = st.text_input("Nota Fiscal:", value=linha_atual["nota_fiscal"], placeholder="Ex: 987654")
    
    salvar = st.form_submit_button("💾 Salvar Alteração", use_container_width=True)
    
    if salvar:
        st.session_state.estoque.at[idx_linha, "status"] = novo_status
        if novo_status == "Vazio":
            st.session_state.estoque.at[idx_linha, "etiqueta"] = ""
            st.session_state.estoque.at[idx_linha, "nota_fiscal"] = ""
        else:
            st.session_state.estoque.at[idx_linha, "etiqueta"] = nova_etiqueta
            st.session_state.estoque.at[idx_linha, "nota_fiscal"] = nova_nf
        st.rerun()

st.sidebar.divider()

# BOTÕES MÁGICOS PARA A APRESENTAÇÃO AO GERENTE
with st.sidebar.expander("🛠️ Ferramentas de Apresentação", expanded=True):
    st.markdown("<small>Use para demonstrar o sistema com dados visuais instantâneos.</small>", unsafe_allow_html=True)
    
    if st.button("🎲 Gerar Dados Fictícios", use_container_width=True):
        st.session_state.estoque["status"] = "Vazio"
        st.session_state.estoque["etiqueta"] = ""
        st.session_state.estoque["nota_fiscal"] = ""
        
        # Preenche ~25% do armazém aleatoriamente
        for idx in st.session_state.estoque.index:
            if random.random() < 0.25:
                st.session_state.estoque.at[idx, "status"] = "Ocupado"
                st.session_state.estoque.at[idx, "etiqueta"] = f"PAL-{random.randint(1000, 9999)}"
                st.session_state.estoque.at[idx, "nota_fiscal"] = f"NF-{random.randint(100000, 999999)}"
        st.rerun()

    if st.button("🧹 Esvaziar Armazém", use_container_width=True):
        st.session_state.estoque["status"] = "Vazio"
        st.session_state.estoque["etiqueta"] = ""
        st.session_state.estoque["nota_fiscal"] = ""
        st.rerun()

# ---------------------------------------------------------
# 4. VISUALIZAÇÃO 3D REALISTA 
# ---------------------------------------------------------
dados_json = json.dumps(st.session_state.estoque.to_dict(orient="records"))

html_3d = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ margin: 0; background: #0b0e14; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden; }}
        #container3d {{ width: 100%; height: 580px; }}
        #tooltip {{
            position: absolute; background: rgba(18, 24, 38, 0.94); border: 1px solid #3d4b68;
            padding: 12px 16px; border-radius: 8px; display: none; pointer-events: none;
            font-size: 13px; z-index: 10; box-shadow: 0 8px 24px rgba(0,0,0,0.6);
            backdrop-filter: blur(8px);
        }}
        #legend {{
            position: absolute; bottom: 15px; left: 15px; background: rgba(15, 20, 31, 0.88);
            border: 1px solid #2a3447; border-radius: 8px; padding: 10px 14px; font-size: 12px;
            display: flex; gap: 15px; align-items: center; backdrop-filter: blur(4px);
        }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 3px; }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="container3d"></div>
    <div id="tooltip"></div>
    <div id="legend">
        <div class="legend-item"><div class="legend-color" style="background:#00ff88; box-shadow:0 0 8px #00ff88;"></div> Livre</div>
        <div class="legend-item"><div class="legend-color" style="background:#ff9900;"></div> Ocupado Geral</div>
        <div class="legend-item"><div class="legend-color" style="background:#ff2a55;"></div> Ocupado Tratativa</div>
        <div class="legend-item"><div class="legend-color" style="background:#1e40af;"></div> Estrutura de Aço (Porta-Palete)</div>
    </div>

    <script>
        const dados = {dados_json};
        
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0b0e14);
        scene.fog = new THREE.FogExp2(0x0b0e14, 0.009);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 580, 0.1, 1000);
        camera.position.set(15, 25, 42);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, 580);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.getElementById('container3d').appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.target.set(15, 3, -3);
        controls.maxPolarAngle = Math.PI / 2 - 0.02;

        scene.add(new THREE.AmbientLight(0xffffff, 0.5));
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.85);
        dirLight.position.set(35, 45, 25);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        scene.add(dirLight);

        const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.35);
        fillLight.position.set(-30, 20, -20);
        scene.add(fillLight);

        const floorGeo = new THREE.PlaneGeometry(140, 90);
        const floorMat = new THREE.MeshStandardMaterial({{ color: 0x111622, roughness: 0.7, metalness: 0.2 }});
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -0.05;
        floor.receiveShadow = true;
        scene.add(floor);

        const grid = new THREE.GridHelper(140, 70, 0x2a354d, 0x182030);
        grid.position.y = -0.04;
        scene.add(grid);

        const matMontanteGeral = new THREE.MeshStandardMaterial({{ color: 0x1e3a8a, metalness: 0.6, roughness: 0.3 }});
        const matMontanteTrat = new THREE.MeshStandardMaterial({{ color: 0x991b1b, metalness: 0.6, roughness: 0.3 }});
        const matLongarina = new THREE.MeshStandardMaterial({{ color: 0xd97706, metalness: 0.5, roughness: 0.4 }});
        const matPaleteMadeira = new THREE.MeshStandardMaterial({{ color: 0x854d0e, roughness: 0.85 }});
        const matOcupadoGeral = new THREE.MeshStandardMaterial({{ color: 0xf59e0b, roughness: 0.4, metalness: 0.1 }});
        const matOcupadoTrat = new THREE.MeshStandardMaterial({{ color: 0xf43f5e, roughness: 0.3, metalness: 0.2, emissive: 0x4c0519 }});
        const matVazioGeral = new THREE.MeshBasicMaterial({{ color: 0x10b981, wireframe: true, transparent: true, opacity: 0.12 }});
        const matVazioTrat = new THREE.MeshBasicMaterial({{ color: 0xf43f5e, wireframe: true, transparent: true, opacity: 0.22 }});

        const boxGeo = new THREE.BoxGeometry(1.05, 0.8, 1.1);
        const palletGeo = new THREE.BoxGeometry(1.15, 0.1, 1.18);
        const colGeo = new THREE.BoxGeometry(0.08, 4.8, 0.08);
        const beamGeoLong = new THREE.BoxGeometry(2.55, 0.08, 0.06); 
        const beamGeoCross = new THREE.BoxGeometry(0.06, 0.06, 1.3);

        const objetosInterativos = [];
        const racksCriados = new Set();

        dados.forEach(item => {{
            let rackX = 40 - (item.col_idx * 2.8);
            let posZ = item.z_pos;
            let rackKey = `${{item.rua}}_${{item.col_idx}}_${{item.z_pos}}`; 

            if (!racksCriados.has(rackKey)) {{
                racksCriados.add(rackKey);
                const rackGroup = new THREE.Group();
                let matColuna = item.zona === "Tratativa" ? matMontanteTrat : matMontanteGeral;

                const offsetsX = [-1.28, 1.28];
                const offsetsZ = [-0.6, 0.6];

                offsetsX.forEach(ox => {{
                    offsetsZ.forEach(oz => {{
                        const colMesh = new THREE.Mesh(colGeo, matColuna);
                        colMesh.position.set(rackX + ox, 2.35, posZ + oz);
                        colMesh.castShadow = true;
                        colMesh.receiveShadow = true;
                        rackGroup.add(colMesh);
                    }});
                }});

                const niveisY = [0.25, 1.65, 3.05];
                niveisY.forEach(ny => {{
                    [-0.6, 0.6].forEach(oz => {{
                        const beam = new THREE.Mesh(beamGeoLong, matLongarina);
                        beam.position.set(rackX, ny, posZ + oz);
                        beam.castShadow = true;
                        rackGroup.add(beam);
                    }});

                    [-1.28, 1.28].forEach(ox => {{
                        const crossBeam = new THREE.Mesh(beamGeoCross, matColuna);
                        crossBeam.position.set(rackX + ox, ny - 0.02, posZ);
                        rackGroup.add(crossBeam);
                    }});
                }});
                scene.add(rackGroup);
            }}

            let posX = (item.side === 'left') ? rackX - 0.62 : rackX + 0.62;
            let posY = (item.nivel / 10) * 1.4 - 0.55;

            const group = new THREE.Group();
            group.position.set(posX, posY, posZ);

            if (item.status === "Ocupado") {{
                const palletMesh = new THREE.Mesh(palletGeo, matPaleteMadeira);
                palletMesh.position.y = -0.4;
                palletMesh.castShadow = true;
                palletMesh.receiveShadow = true;
                group.add(palletMesh);

                let matBox = item.zona === "Tratativa" ? matOcupadoTrat : matOcupadoGeral;
                const boxMesh = new THREE.Mesh(boxGeo, matBox);
                boxMesh.castShadow = true;
                boxMesh.receiveShadow = true;
                boxMesh.userData = item;
                group.add(boxMesh);
                objetosInterativos.push(boxMesh);
            }} else {{
                let matEmpty = item.zona === "Tratativa" ? matVazioTrat : matVazioGeral;
                const emptyMesh = new THREE.Mesh(boxGeo, matEmpty);
                emptyMesh.userData = item;
                group.add(emptyMesh);
                objetosInterativos.push(emptyMesh);
            }}
            scene.add(group);
        }});

        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        const tooltip = document.getElementById('tooltip');

        window.addEventListener('mousemove', (event) => {{
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(objetosInterativos);

            if (intersects.length > 0) {{
                const target = intersects[0].object;
                const d = target.userData;

                document.body.style.cursor = 'pointer';
                tooltip.style.display = 'block';
                tooltip.style.left = (event.clientX + 16) + 'px';
                tooltip.style.top = (event.clientY + 16) + 'px';

                let tagZona = d.zona === 'Tratativa' 
                    ? '<div style="color:#f43f5e; font-weight:bold; margin-bottom:4px; font-size:11px; letter-spacing:1px;">🚨 ZONA DE TRATATIVA</div>' 
                    : '<div style="color:#10b981; font-weight:bold; margin-bottom:4px; font-size:11px; letter-spacing:1px;">📦 ARMAZÉM GERAL</div>';

                let statusBadge = d.status === 'Ocupado'
                    ? '<span style="background:#f59e0b; color:#000; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px;">OCUPADO</span>'
                    : '<span style="background:#10b981; color:#000; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px;">DISPONÍVEL</span>';

                tooltip.innerHTML = `
                    ${{tagZona}}
                    <div style="font-size:15px; font-weight:bold; margin-bottom:6px;">Endereço: ${{d.id}}</div>
                    <div style="margin-bottom:4px;">Status: ${{statusBadge}}</div>
                    <div style="color:#94a3b8; font-size:12px; margin-top:6px;">
                        NF: <span style="color:#fff;">${{d.nota_fiscal || '---'}}</span><br/>
                        Etiqueta: <span style="color:#fff;">${{d.etiqueta || '---'}}</span>
                    </div>
                `;
            }} else {{
                document.body.style.cursor = 'default';
                tooltip.style.display = 'none';
            }}
        }});

        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / 580;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, 580);
        }});
    </script>
</body>
</html>
"""
components.html(html_3d, height=600)

# ---------------------------------------------------------
# 5. TABELA DE CONSULTA ATUALIZADA
# ---------------------------------------------------------
st.subheader("📋 Paletes Alocados")
col_filtro, _ = st.columns([2, 2])
filtro_zona = col_filtro.radio("Filtrar por Zona:", ["Todas", "Armazém", "Tratativa"], horizontal=True)

df_exibir = df[df["status"] == "Ocupado"]
if filtro_zona != "Todas":
    df_exibir = df_exibir[df_exibir["zona"] == filtro_zona]

if df_exibir.empty:
    st.info("Nenhum palete alocado para o filtro selecionado.")
else:
    st.dataframe(df_exibir[["id", "rua", "pos_num", "nivel", "zona", "etiqueta", "nota_fiscal"]], use_container_width=True)